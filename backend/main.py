"""
Budeživo.cz - Cultural Booking SaaS Backend
Modular FastAPI Application with Supabase (PostgreSQL)

Main entry point that initializes the application and registers all routes.
"""
import logging
from fastapi import FastAPI, APIRouter, Depends, HTTPException
from starlette.middleware.cors import CORSMiddleware
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
)
from models.schemas import ContactFormData, InstitutionSettings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Budeživo.cz API",
    description="Multi-tenant SaaS booking system for cultural institutions - Powered by Supabase",
    version="2.0.0"
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
api_router.include_router(availability_router)
api_router.include_router(statistics_router)
api_router.include_router(email_templates_router)
api_router.include_router(public_router)


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


# ============ Middleware ============

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Event Handlers ============

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    if engine:
        await engine.dispose()
    logger.info("Application shutdown - Database connection closed")
