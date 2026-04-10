"""
Budeživo.cz - Cultural Booking SaaS Backend
Modular FastAPI Application with Supabase (PostgreSQL)

Main entry point that initializes the application and registers all routes.
"""
import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import CORS_ORIGINS
from core.security import get_current_user
from database.supabase import get_db, engine
from database.supabase_repositories import InstitutionRepositorySupabase, ContactRepositorySupabase
from routes import (
    auth_router,
    programs_router,
    bookings_router,
    schools_router,
    settings_router,
    team_router,
    dashboard_router,
    payments_router,
    availability_router,
    statistics_router,
    email_templates_router,
    public_router,
    emails_router,
    account_router,
)
from routes.feedback import router as feedback_router
from routes.invitations import router as invitations_router
from routes.legal import router as legal_router
from routes.plan import router as plan_router
from routes.lecturer_availability import router as lecturer_availability_router
from routes.gdpr import router as gdpr_router
from routes.onboarding import router as onboarding_router
from routes.audit import router as audit_router
from routes.calendar_export import router as calendar_export_router
from routes.rooms import router as rooms_router
from routes.microsoft_calendar import router as ms_calendar_router
from models.schemas import ContactFormData, InstitutionSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# Create FastAPI app — disable docs in production
import os as _os
_is_preview = "preview" in _os.environ.get("REACT_APP_BACKEND_URL", "")
app = FastAPI(
    title="Budeživo.cz API",
    version="2.0.0",
    docs_url="/docs" if _is_preview else None,
    redoc_url="/redoc" if _is_preview else None,
    openapi_url="/openapi.json" if _is_preview else None,
)

# Attach rate limiter state and exception handler
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return Response(
        content='{"detail":"Příliš mnoho požadavků. Zkuste to prosím za chvíli."}',
        status_code=429,
        media_type="application/json",
    )

# Create API router with /api prefix
api_router = APIRouter(prefix="/api")

# Register all routes
api_router.include_router(auth_router)
api_router.include_router(programs_router)
api_router.include_router(bookings_router)
api_router.include_router(schools_router)
api_router.include_router(settings_router)
api_router.include_router(team_router)
api_router.include_router(dashboard_router)
api_router.include_router(payments_router)
api_router.include_router(calendar_export_router)
api_router.include_router(availability_router)
api_router.include_router(statistics_router)
api_router.include_router(email_templates_router)
api_router.include_router(public_router)
api_router.include_router(emails_router)
api_router.include_router(account_router)
api_router.include_router(feedback_router)
api_router.include_router(invitations_router)
api_router.include_router(legal_router)
api_router.include_router(plan_router)
api_router.include_router(lecturer_availability_router)
api_router.include_router(gdpr_router)
api_router.include_router(onboarding_router)
api_router.include_router(audit_router)
api_router.include_router(rooms_router)
api_router.include_router(ms_calendar_router)


# ============ Additional Routes ============

@api_router.get("/")
async def root():
    """API root endpoint."""
    return {"message": "KulturaBooking API v2.0 - Supabase Edition"}


@api_router.post("/contact")
async def submit_contact_form(data: ContactFormData, db: AsyncSession = Depends(get_db)):
    """Handle contact form submissions."""
    contact_repo = ContactRepositorySupabase(db)
    contact = await contact_repo.create({
        "name": data.name,
        "email": data.email,
        "institution": data.institution,
        "subject": data.subject,
        "message": data.message,
    })
    
    logger.info(f"Contact form submitted: {data.email} - {data.subject}")
    return {"message": "Message sent successfully", "id": contact["id"]}


# ============ Institution Settings Routes ============

@api_router.get("/institution/settings")
async def get_institution_settings(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get institution settings."""
    institution_repo = InstitutionRepositorySupabase(db)
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@api_router.put("/institution/settings")
async def update_institution_settings(
    data: InstitutionSettings,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update institution settings."""
    institution_repo = InstitutionRepositorySupabase(db)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    result = await institution_repo.update(current_user["institution_id"], update_data)
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Institution not found")
    
    return {"message": "Settings updated"}


# Include API router
app.include_router(api_router)


# ============ Health Check Endpoint ============
# This endpoint is at root level (not under /api) for Railway healthcheck
# It requires no auth and no database connection

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Railway/container orchestration.
    Returns HTTP 200 with status ok - no dependencies.
    """
    return {"status": "ok"}


@app.get("/")
async def app_root():
    """Root endpoint redirect info."""
    return {"message": "Budeživo.cz API", "api": "/api/", "health": "/health"}


# ============ Middleware ============

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

app.add_middleware(SecurityHeadersMiddleware)

# WAF middleware — must be added after CORS (outermost = first to execute)
from middleware.waf import WAFMiddleware
app.add_middleware(WAFMiddleware)


# ============ Event Handlers ============

@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    try:
        from scheduler import start_scheduler
        start_scheduler()
        logger.info("Application startup - Feedback scheduler initialized")
    except Exception as e:
        logger.warning(f"Failed to start scheduler: {e}")

    try:
        from services.storage_service import init_storage
        init_storage()
    except Exception as e:
        logger.warning(f"Object storage init deferred: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    try:
        from scheduler import stop_scheduler
        stop_scheduler()
    except Exception as e:
        logger.warning(f"Failed to stop scheduler: {e}")
    
    if engine:
        await engine.dispose()
    logger.info("Application shutdown - Database connection closed")
