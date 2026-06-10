"""
DynamoDB Service
----------------
Handles storing and retrieving auth events from DynamoDB.

Table schema:
  PK: event_id (string)
  SK: published (ISO timestamp string)
  TTL: auto-expire events after 90 days
  GSI: actor_id-published-index for per-user queries
"""

import boto3
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.models.events import AuthEvent, RiskScore

logger = logging.getLogger(__name__)
settings = get_settings()


class DynamoDBService:

    def __init__(self):
        self.client = boto3.resource(
            "dynamodb",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self.table_name = settings.dynamodb_table_name
        self._table = None

    @property
    def table(self):
        if not self._table:
            self._table = self.client.Table(self.table_name)
        return self._table

    # -------------------------------------------------------------------------
    # Table setup
    # -------------------------------------------------------------------------

    async def ensure_table_exists(self) -> bool:
        """Create the DynamoDB table if it doesn't exist. Safe to call repeatedly."""
        try:
            existing = [t.name for t in self.client.tables.all()]
            if self.table_name in existing:
                logger.info(f"DynamoDB table '{self.table_name}' already exists")
                return True

            logger.info(f"Creating DynamoDB table '{self.table_name}'...")
            table = self.client.create_table(
                TableName=self.table_name,
                BillingMode="PAY_PER_REQUEST",
                AttributeDefinitions=[
                    {"AttributeName": "event_id", "AttributeType": "S"},
                    {"AttributeName": "published", "AttributeType": "S"},
                    {"AttributeName": "actor_id", "AttributeType": "S"},
                ],
                KeySchema=[
                    {"AttributeName": "event_id", "KeyType": "HASH"},
                    {"AttributeName": "published", "KeyType": "RANGE"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "actor_id-published-index",
                        "KeySchema": [
                            {"AttributeName": "actor_id", "KeyType": "HASH"},
                            {"AttributeName": "published", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                    }
                ],
                )
            table.wait_until_exists()

            # TTL must be enabled separately after table creation
            self.client.meta.client.update_time_to_live(
                TableName=self.table_name,
                TimeToLiveSpecification={"AttributeName": "ttl", "Enabled": True},
            )
            logger.info(f"Table '{self.table_name}' created successfully")
            return True

        except ClientError as e:
            logger.error(f"Failed to create DynamoDB table: {e}")
            return False

    # -------------------------------------------------------------------------
    # Event storage
    # -------------------------------------------------------------------------

    async def store_event(self, event: AuthEvent) -> bool:
        """Store a single auth event. Idempotent — safe to call multiple times."""
        try:
            ttl = int(time.time()) + (90 * 24 * 60 * 60)  # 90 days

            item = {
                "event_id": event.event_id,
                "published": event.published.isoformat(),
                "event_type": event.event_type,
                "display_message": event.display_message,
                "severity": event.severity,
                "actor_id": event.actor_id or "unknown",
                "actor_name": event.actor_name or "",
                "outcome": event.outcome or "",
                "outcome_reason": event.outcome_reason or "",
                "ip_address": event.ip_address or "",
                "ttl": ttl,
            }

            # Add geolocation if present
            if event.geolocation:
                item["geo_city"] = event.geolocation.city or ""
                item["geo_country"] = event.geolocation.country or ""
                item["geo_state"] = event.geolocation.state or ""

            # Add device info if present
            if event.device:
                item["device_os"] = event.device.os or ""
                item["device_browser"] = event.device.browser or ""

            self.table.put_item(Item=item)
            return True

        except ClientError as e:
            logger.error(f"Failed to store event {event.event_id}: {e}")
            return False

    async def store_events_batch(self, events: list[AuthEvent]) -> int:
        """Store multiple events efficiently using batch write. Returns count stored."""
        stored = 0
        # DynamoDB batch_writer handles chunking into 25-item batches automatically
        try:
            with self.table.batch_writer() as batch:
                for event in events:
                    ttl = int(time.time()) + (90 * 24 * 60 * 60)
                    item = {
                        "event_id": event.event_id,
                        "published": event.published.isoformat(),
                        "event_type": event.event_type,
                        "display_message": event.display_message,
                        "severity": event.severity,
                        "actor_id": event.actor_id or "unknown",
                        "actor_name": event.actor_name or "",
                        "outcome": event.outcome or "",
                        "ip_address": event.ip_address or "",
                        "ttl": ttl,
                    }
                    if event.geolocation:
                        item["geo_country"] = event.geolocation.country or ""
                        item["geo_city"] = event.geolocation.city or ""
                    batch.put_item(Item=item)
                    stored += 1

            logger.info(f"Batch stored {stored} events to DynamoDB")
            return stored

        except ClientError as e:
            logger.error(f"Batch write failed: {e}")
            return stored

    # -------------------------------------------------------------------------
    # Event retrieval
    # -------------------------------------------------------------------------

    async def get_recent_events(self, limit: int = 100) -> list[dict]:
        """Scan for recent events. For production use a GSI on published timestamp."""
        try:
            response = self.table.scan(Limit=limit)
            items = response.get("Items", [])
            # Sort by published descending
            items.sort(key=lambda x: x.get("published", ""), reverse=True)
            return items[:limit]
        except ClientError as e:
            logger.error(f"Failed to get recent events: {e}")
            return []

    async def get_events_by_user(self, actor_id: str, limit: int = 50) -> list[dict]:
        """Query events for a specific user using the GSI."""
        try:
            from boto3.dynamodb.conditions import Key
            response = self.table.query(
                IndexName="actor_id-published-index",
                KeyConditionExpression=Key("actor_id").eq(actor_id),
                ScanIndexForward=False,  # Descending order
                Limit=limit,
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get events for user {actor_id}: {e}")
            return []

    async def get_failed_events(self, limit: int = 50) -> list[dict]:
        """Scan for failed authentication events."""
        try:
            from boto3.dynamodb.conditions import Attr
            response = self.table.scan(
                FilterExpression=Attr("outcome").eq("FAILURE"),
                Limit=limit * 3,  # Over-fetch since scan + filter is inefficient
            )
            items = response.get("Items", [])
            items.sort(key=lambda x: x.get("published", ""), reverse=True)
            return items[:limit]
        except ClientError as e:
            logger.error(f"Failed to get failed events: {e}")
            return []

    async def get_event_count(self) -> int:
        """Get approximate total event count from table metadata."""
        try:
            self.table.reload()
            return self.table.item_count
        except ClientError:
            return 0

    # -------------------------------------------------------------------------
    # Risk score storage
    # -------------------------------------------------------------------------

    async def store_risk_score(self, risk: RiskScore) -> bool:
        """Store a risk score for historical tracking."""
        try:
            risk_table = self.client.Table(f"{self.table_name}-risk-scores")
            ttl = int(time.time()) + (7 * 24 * 60 * 60)  # 7 days
            risk_table.put_item(Item={
                "user_id": risk.user_id,
                "timestamp": risk.timestamp.isoformat(),
                "score": str(risk.score),
                "level": risk.level.value,
                "factors": risk.factors,
                "ttl": ttl,
            })
            return True
        except ClientError as e:
            logger.error(f"Failed to store risk score: {e}")
            return False
