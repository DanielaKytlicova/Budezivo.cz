"""
Repository pattern for database operations.
Each repository encapsulates all database queries for a specific entity.
This abstraction makes it easier to migrate from MongoDB to Supabase.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from .mongodb import get_database


class BaseRepository:
    """Base repository with common operations."""
    
    collection_name: str = None
    
    def __init__(self):
        self.db = get_database()
    
    @property
    def collection(self):
        return self.db[self.collection_name]
    
    async def find_one(self, query: dict, projection: dict = None) -> Optional[dict]:
        """Find single document."""
        if projection is None:
            projection = {"_id": 0}
        return await self.collection.find_one(query, projection)
    
    async def find_many(self, query: dict, projection: dict = None, limit: int = 1000) -> List[dict]:
        """Find multiple documents."""
        if projection is None:
            projection = {"_id": 0}
        return await self.collection.find(query, projection).to_list(limit)
    
    async def insert_one(self, document: dict) -> dict:
        """Insert single document."""
        await self.collection.insert_one(document)
        return document
    
    async def update_one(self, query: dict, update: dict) -> int:
        """Update single document. Returns matched count."""
        result = await self.collection.update_one(query, {"$set": update})
        return result.matched_count
    
    async def delete_one(self, query: dict) -> int:
        """Delete single document. Returns deleted count."""
        result = await self.collection.delete_one(query)
        return result.deleted_count
    
    async def count(self, query: dict) -> int:
        """Count documents matching query."""
        return await self.collection.count_documents(query)


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    collection_name = "users"
    
    async def find_by_email(self, email: str) -> Optional[dict]:
        """Find user by email."""
        return await self.find_one({"email": email})
    
    async def find_by_id(self, user_id: str) -> Optional[dict]:
        """Find user by ID, excluding password hash."""
        return await self.find_one(
            {"id": user_id},
            {"_id": 0, "password_hash": 0}
        )
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all users in an institution."""
        return await self.collection.find(
            {"institution_id": institution_id},
            {"_id": 0, "password_hash": 0}
        ).to_list(100)
    
    async def create(self, user_data: dict) -> dict:
        """Create new user."""
        user_data["id"] = str(uuid.uuid4())
        user_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(user_data)
    
    async def update_role(self, user_id: str, institution_id: str, role: str) -> int:
        """Update user role."""
        return await self.update_one(
            {"id": user_id, "institution_id": institution_id},
            {"role": role}
        )
    
    async def delete_by_id(self, user_id: str, institution_id: str) -> int:
        """Delete user by ID."""
        return await self.delete_one({"id": user_id, "institution_id": institution_id})


class InstitutionRepository(BaseRepository):
    """Repository for institution operations."""
    
    collection_name = "institutions"
    
    async def find_by_id(self, institution_id: str) -> Optional[dict]:
        """Find institution by ID."""
        return await self.find_one({"id": institution_id})
    
    async def create(self, institution_data: dict) -> dict:
        """Create new institution."""
        institution_data["id"] = str(uuid.uuid4())
        institution_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(institution_data)
    
    async def update(self, institution_id: str, update_data: dict) -> int:
        """Update institution."""
        return await self.update_one({"id": institution_id}, update_data)
    
    async def update_pro_settings(self, institution_id: str, pro_settings: dict) -> int:
        """Update PRO settings."""
        return await self.update_one(
            {"id": institution_id},
            {"pro_settings": pro_settings}
        )


class ProgramRepository(BaseRepository):
    """Repository for program operations."""
    
    collection_name = "programs"
    
    async def find_by_id(self, program_id: str, institution_id: str = None) -> Optional[dict]:
        """Find program by ID."""
        query = {"id": program_id}
        if institution_id:
            query["institution_id"] = institution_id
        return await self.find_one(query)
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all programs for an institution."""
        return await self.find_many({"institution_id": institution_id})
    
    async def find_public(self, institution_id: str) -> List[dict]:
        """Find all active published programs for public booking."""
        return await self.find_many({
            "institution_id": institution_id,
            "status": "active"
        })
    
    async def create(self, program_data: dict, institution_id: str) -> dict:
        """Create new program."""
        program_data["id"] = str(uuid.uuid4())
        program_data["institution_id"] = institution_id
        program_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(program_data)
    
    async def update(self, program_id: str, institution_id: str, update_data: dict) -> int:
        """Update program."""
        return await self.update_one(
            {"id": program_id, "institution_id": institution_id},
            update_data
        )
    
    async def delete(self, program_id: str, institution_id: str) -> int:
        """Delete program."""
        return await self.delete_one({"id": program_id, "institution_id": institution_id})


class BookingRepository(BaseRepository):
    """Repository for booking/reservation operations."""
    
    collection_name = "bookings"
    
    async def find_by_id(self, booking_id: str, institution_id: str) -> Optional[dict]:
        """Find booking by ID."""
        return await self.find_one({
            "id": booking_id,
            "institution_id": institution_id
        })
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all bookings for an institution, sorted by created_at desc."""
        return await self.collection.find(
            {"institution_id": institution_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(1000)
    
    async def find_by_date(self, institution_id: str, date: str) -> List[dict]:
        """Find bookings for specific date."""
        return await self.find_many({
            "institution_id": institution_id,
            "date": date,
            "status": {"$ne": "cancelled"}
        })
    
    async def find_by_program_and_date(
        self, institution_id: str, program_id: str, date: str
    ) -> List[dict]:
        """Find bookings for a program on specific date."""
        return await self.find_many({
            "institution_id": institution_id,
            "program_id": program_id,
            "date": date,
            "status": {"$ne": "cancelled"}
        })
    
    async def count_today(self, institution_id: str, today: str) -> int:
        """Count today's non-cancelled bookings."""
        return await self.count({
            "institution_id": institution_id,
            "date": today,
            "status": {"$ne": "cancelled"}
        })
    
    async def count_upcoming(self, institution_id: str, today: str) -> int:
        """Count upcoming non-cancelled bookings."""
        return await self.count({
            "institution_id": institution_id,
            "date": {"$gte": today},
            "status": {"$ne": "cancelled"}
        })
    
    async def count_month(self, institution_id: str, month_prefix: str) -> int:
        """Count bookings created this month."""
        return await self.count({
            "institution_id": institution_id,
            "created_at": {"$regex": f"^{month_prefix}"}
        })
    
    async def create(self, booking_data: dict, institution_id: str) -> dict:
        """Create new booking."""
        booking_data["id"] = str(uuid.uuid4())
        booking_data["institution_id"] = institution_id
        booking_data["status"] = "pending"
        booking_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(booking_data)
    
    async def update(self, booking_id: str, institution_id: str, update_data: dict) -> int:
        """Update booking."""
        return await self.update_one(
            {"id": booking_id, "institution_id": institution_id},
            update_data
        )
    
    async def update_status(self, booking_id: str, institution_id: str, status: str) -> int:
        """Update booking status."""
        return await self.update(booking_id, institution_id, {"status": status})
    
    async def assign_lecturer(
        self, booking_id: str, institution_id: str, 
        lecturer_id: str, lecturer_name: str
    ) -> int:
        """Assign lecturer to booking."""
        return await self.update(booking_id, institution_id, {
            "assigned_lecturer_id": lecturer_id,
            "assigned_lecturer_name": lecturer_name,
            "assigned_lecturer_at": datetime.now(timezone.utc).isoformat()
        })
    
    async def unassign_lecturer(self, booking_id: str, institution_id: str) -> int:
        """Remove lecturer assignment from booking."""
        return await self.update(booking_id, institution_id, {
            "assigned_lecturer_id": None,
            "assigned_lecturer_name": None,
            "assigned_lecturer_at": None
        })


class SchoolRepository(BaseRepository):
    """Repository for school/CRM operations."""
    
    collection_name = "schools"
    
    async def find_by_institution(self, institution_id: str) -> List[dict]:
        """Find all schools for an institution."""
        return await self.find_many({"institution_id": institution_id})
    
    async def find_by_email(self, institution_id: str, email: str) -> Optional[dict]:
        """Find school by email in institution."""
        return await self.find_one({
            "institution_id": institution_id,
            "email": email
        })
    
    async def find_by_ids(self, institution_id: str, school_ids: List[str]) -> List[dict]:
        """Find schools by IDs."""
        return await self.find_many({
            "institution_id": institution_id,
            "id": {"$in": school_ids}
        })
    
    async def create(self, school_data: dict, institution_id: str) -> dict:
        """Create new school."""
        school_data["id"] = str(uuid.uuid4())
        school_data["institution_id"] = institution_id
        school_data["booking_count"] = 1
        school_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(school_data)
    
    async def increment_booking_count(self, school_id: str) -> None:
        """Increment booking count for school."""
        await self.collection.update_one(
            {"id": school_id},
            {"$inc": {"booking_count": 1}}
        )


class ThemeRepository(BaseRepository):
    """Repository for theme settings operations."""
    
    collection_name = "theme_settings"
    
    async def find_by_institution(self, institution_id: str) -> Optional[dict]:
        """Find theme settings for institution."""
        return await self.find_one({"institution_id": institution_id})
    
    async def create_or_update(self, institution_id: str, theme_data: dict) -> dict:
        """Create or update theme settings."""
        theme_data["institution_id"] = institution_id
        await self.collection.update_one(
            {"institution_id": institution_id},
            {"$set": theme_data},
            upsert=True
        )
        return await self.find_by_institution(institution_id)


class PaymentRepository(BaseRepository):
    """Repository for payment transactions."""
    
    collection_name = "payment_transactions"
    
    async def find_by_session(self, session_id: str, institution_id: str) -> Optional[dict]:
        """Find payment by session ID."""
        return await self.find_one({
            "session_id": session_id,
            "institution_id": institution_id
        })
    
    async def create(self, payment_data: dict) -> dict:
        """Create payment record."""
        payment_data["id"] = str(uuid.uuid4())
        payment_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(payment_data)
    
    async def update_status(self, session_id: str, status: str, payment_status: str) -> int:
        """Update payment status."""
        result = await self.collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": status, "payment_status": payment_status}}
        )
        return result.matched_count


class ContactRepository(BaseRepository):
    """Repository for contact messages."""
    
    collection_name = "contact_messages"
    
    async def create(self, contact_data: dict) -> dict:
        """Create contact message."""
        contact_data["id"] = str(uuid.uuid4())
        contact_data["status"] = "new"
        contact_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return await self.insert_one(contact_data)


class SettingsRepository(BaseRepository):
    """Repository for institution settings."""
    
    collection_name = "institution_settings"
    
    async def update_notifications(self, institution_id: str, settings: dict) -> None:
        """Update notification settings."""
        await self.collection.update_one(
            {"institution_id": institution_id},
            {"$set": {"notifications": settings}},
            upsert=True
        )
    
    async def update_locale(self, institution_id: str, settings: dict) -> None:
        """Update locale settings."""
        await self.collection.update_one(
            {"institution_id": institution_id},
            {"$set": {"locale": settings}},
            upsert=True
        )
    
    async def update_gdpr(self, institution_id: str, settings: dict) -> None:
        """Update GDPR settings."""
        await self.collection.update_one(
            {"institution_id": institution_id},
            {"$set": {"gdpr": settings}},
            upsert=True
        )
