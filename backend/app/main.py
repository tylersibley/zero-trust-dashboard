"""
Zero Trust Dashboard – FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os
from app.core.config import get_settings
from app.api import events, users, risk, health, webhooks, ml
from app.services.dynamodb_service import DynamoDBService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Zero Trust Dashboard API [{settings.app_env}]")
    if settings.aws_access_key_id and settings.aws_access_key_id != "your_access_key_here":
        db = DynamoDBService()
        await db.ensure_table_exists()
        logger.info("DynamoDB initialized")
    else:
        logger.warning("AWS credentials not configured – DynamoDB storage disabled")
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
- ML anomaly detection using Isolation Forest (scikit-learn)
- User risk scoring and behavioral baselines
- Zero Trust policy simulation
    """,
    version="3.0.0",
    lifespan=lifespan,
)

# Build CORS origins list from env var + defaults
default_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://*.vercel.app",
    "https://zero-trust-dashboard-sooty.vercel.app",
    "https://tylersibley.dev",
]
extra = os.environ.get("ALLOWED_ORIGINS", "")
if extra:
    default_origins.extend([o.strip() for o in extra.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(users.router, prefix="/api/v1", tags=["Users"])
app.include_router(risk.router, prefix="/api/v1", tags=["Risk"])
app.include_router(webhooks.router, prefix="/api/v1", tags=["Webhooks"])
app.include_router(ml.router, prefix="/api/v1", tags=["ML Anomaly Detection"])

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
