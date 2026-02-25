"""
Budeživo.cz - Cultural Booking SaaS Backend
Modular FastAPI Application

Main entry point that initializes the application and registers all routes.
"""
import logging
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from core.config import CORS_ORIGINS
from database.mongodb import close_mongodb_connection
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
)
from models.schemas import ContactFormData
from database.repositories import ContactRepository, InstitutionRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Budeživo.cz API",
    description="Multi-tenant SaaS booking system for cultural institutions",
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


# ============ Additional Routes ============

@api_router.get("/")
async def root():
    """API root endpoint."""
    return {"message": "KulturaBooking API v2.0 - Modular Architecture"}


@api_router.post("/contact")
async def submit_contact_form(data: ContactFormData):
    """Handle contact form submissions."""
    contact_repo = ContactRepository()
    contact = await contact_repo.create({
        "name": data.name,
        "email": data.email,
        "institution": data.institution,
        "subject": data.subject,
        "message": data.message,
    })
    
    logger.info(f"Contact form submitted: {data.email} - {data.subject}")
    return {"message": "Message sent successfully", "id": contact["id"]}


@api_router.get("/institution/settings")
async def get_institution_settings_route():
    """Get institution settings - redirect handled by settings router."""
    # This endpoint is handled via Depends in original code
    # Keeping for backwards compatibility
    pass


@api_router.put("/institution/settings")
async def update_institution_settings_route():
    """Update institution settings - redirect handled by settings router."""
    pass


# Include API router
app.include_router(api_router)


# ============ Institution Settings Routes (kept at top level for compatibility) ============

from fastapi import Depends
from core.security import get_current_user
from models.schemas import InstitutionSettings


@api_router.get("/institution/settings")
async def get_institution_settings(current_user: dict = Depends(get_current_user)):
    """Get institution settings."""
    institution_repo = InstitutionRepository()
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Institution not found")
    return institution


@api_router.put("/institution/settings")
async def update_institution_settings(
    data: InstitutionSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update institution settings."""
    institution_repo = InstitutionRepository()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    result = await institution_repo.update(current_user["institution_id"], update_data)
    
    if result == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Institution not found")
    
    return {"message": "Settings updated"}


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
    await close_mongodb_connection()
    logger.info("Application shutdown - MongoDB connection closed")
