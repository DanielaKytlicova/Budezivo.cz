from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'change_this_secret_key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days

# Stripe configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# Security
security = HTTPBearer()

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ============ Models ============

class UserBase(BaseModel):
    email: EmailStr
    institution_name: str
    institution_type: str
    country: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    institution_id: str
    role: str = "admin"
    created_at: datetime

class TokenResponse(BaseModel):
    token: str
    user: Dict[str, Any]

class ProgramBase(BaseModel):
    name_cs: str
    name_en: str
    description_cs: str
    description_en: str
    duration: int  # minutes
    age_group: str  # "ms_3_6", "zs1_7_12", "zs2_12_15", "ss_14_18", "gym_14_18", "adults"
    min_capacity: int = 5
    max_capacity: int = 30
    target_group: str  # "schools" or "public"
    price: Optional[float] = 0.0
    status: str = "active"

class ProgramCreate(ProgramBase):
    pass

class Program(ProgramBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    created_at: datetime

class BookingBase(BaseModel):
    program_id: str
    date: str
    time_block: str  # "08:00-09:00", "09:00-10:30", etc.
    school_name: str
    group_type: str  # "ms_3_6", "zs1_7_12", etc.
    age_or_class: str  # "3-4 roky" or "4.A"
    num_students: int
    special_requirements: Optional[str] = ""
    contact_name: str
    contact_email: EmailStr
    contact_phone: str
    gdpr_consent: bool = True

class BookingCreate(BookingBase):
    pass

class Booking(BookingBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    status: str = "pending"
    created_at: datetime

class SchoolBase(BaseModel):
    name: str
    contact_person: str
    email: EmailStr
    phone: str

class School(SchoolBase):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    booking_count: int = 0
    created_at: datetime

class ThemeSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    institution_id: str
    primary_color: str = "#1E293B"
    secondary_color: str = "#84A98C"
    accent_color: str = "#E9C46A"
    logo_url: Optional[str] = None
    header_style: str = "light"
    footer_text: Optional[str] = None

class ThemeUpdate(BaseModel):
    primary_color: str = "#1E293B"
    secondary_color: str = "#84A98C"
    accent_color: str = "#E9C46A"
    logo_url: Optional[str] = None
    header_style: str = "light"
    footer_text: Optional[str] = None

class PaymentTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    institution_id: str
    user_id: str
    session_id: str
    amount: float
    currency: str
    package: str
    status: str
    payment_status: str
    created_at: datetime

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class DashboardStats(BaseModel):
    today_bookings: int
    upcoming_groups: int
    capacity_usage: float
    bookings_used: int
    bookings_limit: int

class PaymentSessionCreate(BaseModel):
    package: str  # "basic", "standard", "premium"
    billing_cycle: str  # "monthly", "yearly"

# ============ Helpers ============

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: str, institution_id: str, email: str) -> str:
    payload = {
        "user_id": user_id,
        "institution_id": institution_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============ Auth Routes ============

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create institution
    institution_id = str(uuid.uuid4())
    institution = {
        "id": institution_id,
        "name": user_data.institution_name,
        "type": user_data.institution_type,
        "country": user_data.country,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.institutions.insert_one(institution)

    # Create user
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "institution_id": institution_id,
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)

    # Create default theme settings
    theme = {
        "institution_id": institution_id,
        "primary_color": "#1E293B",
        "secondary_color": "#84A98C",
        "accent_color": "#E9C46A",
        "logo_url": None,
        "header_style": "light",
        "footer_text": None
    }
    await db.theme_settings.insert_one(theme)

    # Create JWT token
    token = create_jwt_token(user_id, institution_id, user_data.email)

    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": user_data.email,
            "institution_id": institution_id,
            "institution_name": user_data.institution_name,
            "role": "admin"
        }
    }

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    institution = await db.institutions.find_one({"id": user["institution_id"]}, {"_id": 0})

    token = create_jwt_token(user["id"], user["institution_id"], user["email"])

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "institution_id": user["institution_id"],
            "institution_name": institution["name"] if institution else "",
            "role": user["role"]
        }
    }

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    # Mock implementation - in production, send real email
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If email exists, password reset link has been sent"}
    
    # TODO: Send email with reset link
    logging.info(f"Password reset requested for {data.email}")
    return {"message": "If email exists, password reset link has been sent"}

@api_router.get("/auth/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    return {"valid": True, "user": current_user}

# ============ Dashboard Routes ============

@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    institution_id = current_user["institution_id"]
    today = datetime.now(timezone.utc).date().isoformat()

    # Today's bookings
    today_bookings = await db.bookings.count_documents({
        "institution_id": institution_id,
        "date": today,
        "status": {"$ne": "cancelled"}
    })

    # Upcoming groups (next 7 days)
    upcoming_groups = await db.bookings.count_documents({
        "institution_id": institution_id,
        "date": {"$gte": today},
        "status": {"$ne": "cancelled"}
    })

    # Bookings used this month
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    bookings_used = await db.bookings.count_documents({
        "institution_id": institution_id,
        "created_at": {"$regex": f"^{current_month}"}
    })

    # For now, default to free plan limit
    bookings_limit = 50

    # Capacity usage (simplified)
    capacity_usage = min(100.0, (bookings_used / bookings_limit) * 100)

    return {
        "today_bookings": today_bookings,
        "upcoming_groups": upcoming_groups,
        "capacity_usage": capacity_usage,
        "bookings_used": bookings_used,
        "bookings_limit": bookings_limit
    }

# ============ Programs Routes ============

@api_router.post("/programs", response_model=Program)
async def create_program(program_data: ProgramCreate, current_user: dict = Depends(get_current_user)):
    program_id = str(uuid.uuid4())
    program = {
        "id": program_id,
        "institution_id": current_user["institution_id"],
        **program_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.programs.insert_one(program)
    return program

@api_router.get("/programs", response_model=List[Program])
async def get_programs(current_user: dict = Depends(get_current_user)):
    programs = await db.programs.find(
        {"institution_id": current_user["institution_id"]},
        {"_id": 0}
    ).to_list(1000)
    return programs

@api_router.get("/programs/public/{institution_id}", response_model=List[Program])
async def get_public_programs(institution_id: str):
    # Handle demo institution
    if institution_id == "demo":
        return [
            {
                "id": "demo-1",
                "institution_id": "demo",
                "name_cs": "Seznam se s galerií",
                "name_en": "Gallery Introduction",
                "description_cs": "Interaktivní program, který seznámí děti se světem výtvarného umění. Prohlídka bude doplněna praktickými ukázkami a aktivitami.",
                "description_en": "Interactive program introducing children to the world of visual arts with practical demonstrations.",
                "duration": 60,
                "age_group": "zs1_7_12",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 50.0,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "demo-2",
                "institution_id": "demo",
                "name_cs": "Po stopách historie",
                "name_en": "Following History",
                "description_cs": "Tematická prohlídka zaměřená na historii města a regionu. Program je uzpůsoben věku a znalostem žáků.",
                "description_en": "Themed tour focused on city and regional history, adapted to age and knowledge level.",
                "duration": 90,
                "age_group": "zs2_12_15",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 80.0,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "id": "demo-3",
                "institution_id": "demo",
                "name_cs": "Za uměním do neznáma",
                "name_en": "Art Adventure",
                "description_cs": "Kreativní workshop kombinující prohlídku expozice s praktickou tvorbou. Účastníci si vytvoří vlastní umělecké dílo.",
                "description_en": "Creative workshop combining exhibition tour with practical art creation.",
                "duration": 90,
                "age_group": "ss_14_18",
                "min_capacity": 5,
                "max_capacity": 30,
                "target_group": "schools",
                "price": 90.0,
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
    
    programs = await db.programs.find(
        {"institution_id": institution_id, "status": "active"},
        {"_id": 0}
    ).to_list(1000)
    return programs

@api_router.get("/programs/{program_id}", response_model=Program)
async def get_program(program_id: str, current_user: dict = Depends(get_current_user)):
    program = await db.programs.find_one(
        {"id": program_id, "institution_id": current_user["institution_id"]},
        {"_id": 0}
    )
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program

@api_router.put("/programs/{program_id}", response_model=Program)
async def update_program(program_id: str, program_data: ProgramCreate, current_user: dict = Depends(get_current_user)):
    result = await db.programs.update_one(
        {"id": program_id, "institution_id": current_user["institution_id"]},
        {"$set": program_data.model_dump()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    
    program = await db.programs.find_one({"id": program_id}, {"_id": 0})
    return program

@api_router.delete("/programs/{program_id}")
async def delete_program(program_id: str, current_user: dict = Depends(get_current_user)):
    result = await db.programs.delete_one({
        "id": program_id,
        "institution_id": current_user["institution_id"]
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Program not found")
    return {"message": "Program deleted"}

# ============ Bookings Routes ============

@api_router.post("/bookings", response_model=Booking)
async def create_booking(booking_data: BookingCreate, current_user: dict = Depends(get_current_user)):
    booking_id = str(uuid.uuid4())
    booking = {
        "id": booking_id,
        "institution_id": current_user["institution_id"],
        **booking_data.model_dump(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bookings.insert_one(booking)
    return booking

@api_router.post("/bookings/public/{institution_id}", response_model=Booking)
async def create_public_booking(institution_id: str, booking_data: BookingCreate):
    # Handle demo institution - don't save to database
    if institution_id == "demo":
        booking_id = str(uuid.uuid4())
        demo_booking = {
            "id": booking_id,
            "institution_id": "demo",
            **booking_data.model_dump(),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        logging.info(f"Demo booking created: {booking_id} for {booking_data.contact_email}")
        return demo_booking
    
    # Public booking without authentication
    booking_id = str(uuid.uuid4())
    booking = {
        "id": booking_id,
        "institution_id": institution_id,
        **booking_data.model_dump(),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.bookings.insert_one(booking)
    
    # Create or update school record
    school = await db.schools.find_one({
        "institution_id": institution_id,
        "email": booking_data.contact_email
    }, {"_id": 0})
    
    if school:
        await db.schools.update_one(
            {"id": school["id"]},
            {"$inc": {"booking_count": 1}}
        )
    else:
        school_id = str(uuid.uuid4())
        new_school = {
            "id": school_id,
            "institution_id": institution_id,
            "name": booking_data.school_name,
            "contact_person": booking_data.contact_name,
            "email": booking_data.contact_email,
            "phone": booking_data.contact_phone,
            "booking_count": 1,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.schools.insert_one(new_school)
    
    # Mock email notification
    logging.info(f"Booking created: {booking_id} for {booking_data.contact_email}")
    
    return booking

@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(current_user: dict = Depends(get_current_user)):
    bookings = await db.bookings.find(
        {"institution_id": current_user["institution_id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(1000)
    return bookings

@api_router.get("/bookings/{booking_id}", response_model=Booking)
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    booking = await db.bookings.find_one(
        {"id": booking_id, "institution_id": current_user["institution_id"]},
        {"_id": 0}
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@api_router.patch("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    result = await db.bookings.update_one(
        {"id": booking_id, "institution_id": current_user["institution_id"]},
        {"$set": {"status": status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"message": "Status updated"}

# ============ Schools Routes ============

@api_router.get("/schools", response_model=List[School])
async def get_schools(current_user: dict = Depends(get_current_user)):
    schools = await db.schools.find(
        {"institution_id": current_user["institution_id"]},
        {"_id": 0}
    ).to_list(1000)
    return schools

# ============ Statistics Routes ============

@api_router.get("/statistics/bookings-over-time")
async def get_bookings_over_time(current_user: dict = Depends(get_current_user)):
    # Simplified: return mock data for last 6 months
    return {
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "data": [45, 52, 38, 65, 73, 58]
    }

@api_router.get("/statistics/popular-programs")
async def get_popular_programs(current_user: dict = Depends(get_current_user)):
    # Mock data
    return {
        "labels": ["Program A", "Program B", "Program C"],
        "data": [125, 98, 67]
    }

# ============ Theme Settings Routes ============

@api_router.get("/settings/theme")
async def get_theme_settings(current_user: dict = Depends(get_current_user)):
    theme = await db.theme_settings.find_one(
        {"institution_id": current_user["institution_id"]},
        {"_id": 0}
    )
    if not theme:
        theme = {
            "institution_id": current_user["institution_id"],
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": None
        }
    return theme

@api_router.get("/settings/theme/public/{institution_id}")
async def get_public_theme_settings(institution_id: str):
    # Handle demo institution
    if institution_id == "demo":
        return {
            "institution_id": "demo",
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": "Demo Muzeum - Ukázkový rezervační systém"
        }
    
    theme = await db.theme_settings.find_one(
        {"institution_id": institution_id},
        {"_id": 0}
    )
    if not theme:
        theme = {
            "institution_id": institution_id,
            "primary_color": "#1E293B",
            "secondary_color": "#84A98C",
            "accent_color": "#E9C46A",
            "logo_url": None,
            "header_style": "light",
            "footer_text": None
        }
    return theme

@api_router.put("/settings/theme", response_model=ThemeSettings)
async def update_theme_settings(theme_data: ThemeUpdate, current_user: dict = Depends(get_current_user)):
    theme_dict = theme_data.model_dump()
    theme_dict["institution_id"] = current_user["institution_id"]
    
    await db.theme_settings.update_one(
        {"institution_id": current_user["institution_id"]},
        {"$set": theme_dict},
        upsert=True
    )
    
    # Return the complete theme settings
    updated_theme = await db.theme_settings.find_one(
        {"institution_id": current_user["institution_id"]},
        {"_id": 0}
    )
    return updated_theme

# ============ Payment Routes ============

PACKAGE_PRICES = {
    "basic": {"monthly": 990.0, "yearly": 9900.0},
    "standard": {"monthly": 1990.0, "yearly": 19900.0},
    "premium": {"monthly": 3990.0, "yearly": 39900.0}
}

@api_router.post("/payments/create-session")
async def create_payment_session(
    payment_data: PaymentSessionCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    if payment_data.package not in PACKAGE_PRICES:
        raise HTTPException(status_code=400, detail="Invalid package")
    
    amount = PACKAGE_PRICES[payment_data.package][payment_data.billing_cycle]
    
    # Get origin from request
    origin = str(request.base_url).rstrip('/')
    success_url = f"{origin}/admin/plan/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/admin/plan"
    
    # Initialize Stripe checkout
    webhook_url = f"{origin}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="czk",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "institution_id": current_user["institution_id"],
            "user_id": current_user["user_id"],
            "package": payment_data.package,
            "billing_cycle": payment_data.billing_cycle
        }
    )
    
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    transaction_id = str(uuid.uuid4())
    transaction = {
        "id": transaction_id,
        "institution_id": current_user["institution_id"],
        "user_id": current_user["user_id"],
        "session_id": session.session_id,
        "amount": amount,
        "currency": "czk",
        "package": payment_data.package,
        "status": "pending",
        "payment_status": "initiated",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payment_transactions.insert_one(transaction)
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str, current_user: dict = Depends(get_current_user)):
    # Check transaction
    transaction = await db.payment_transactions.find_one(
        {"session_id": session_id, "institution_id": current_user["institution_id"]},
        {"_id": 0}
    )
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # If already paid, return immediately
    if transaction["payment_status"] == "paid":
        return transaction
    
    # Initialize Stripe checkout
    webhook_url = f"{str(os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001'))}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    # Get checkout status
    checkout_status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
    
    # Update transaction
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "status": checkout_status.status,
                "payment_status": checkout_status.payment_status
            }
        }
    )
    
    transaction["status"] = checkout_status.status
    transaction["payment_status"] = checkout_status.payment_status
    
    return transaction

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")
    
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": webhook_response.session_id},
            {
                "$set": {
                    "status": webhook_response.event_type,
                    "payment_status": webhook_response.payment_status
                }
            }
        )
        
        logging.info(f"Webhook processed: {webhook_response.event_type}")
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# ============ Root Routes ============

@api_router.get("/")
async def root():
    return {"message": "KulturaBooking API v1.0"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
