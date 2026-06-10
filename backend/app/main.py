"""
Zero Trust Dashboard — FastAPI Application
------------------------------------------
Main entry point for both local development and AWS Lambda.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.core.config import get_settings
from app.api import events, users, risk, health, webhooks
from app.services.dynamodb_service import DynamoDBService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Zero Trust Dashboard API [{settings.app_env}]")

    # Initialize DynamoDB table on startup
    if settings.aws_access_key_id and settings.aws_access_key_id != "your_access_key_here":
        db = DynamoDBService()
        await db.ensure_table_exists()
        logger.info("DynamoDB initialized")
    else:
        logger.warning("AWS credentials not configured — DynamoDB storage disabled")

    yield
    logger.info("Shutting down Zero Trust Dashboard API")


app = FastAPI(
    title="Zero Trust Security Dashboard",
    description="""
Real-time security monitoring dashboard powered by Okta APIs.

Features:
- Live authentication event stream from Okta System Log
- DynamoDB-backed event storage with 90-day retention
- Real-time event ingestion via Okta Event Hooks
- User risk scoring and anomaly detection
- MFA adoption and compliance metrics
- Zero Trust policy simulation
    """,
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://*.cloudfront.net",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    handler = None
