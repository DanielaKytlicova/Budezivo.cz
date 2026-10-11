"""Internal CRM. No tenant foreign keys or access to booking tables."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Integer, Float, Boolean, DateTime, Date, ForeignKey, JSON, CheckConstraint, Index
from database.models import Base


def now():
    return datetime.now(timezone.utc)


class LeadAccount(Base):
    __tablename__ = 'lead_accounts'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(80), nullable=False, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    password_hash = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    role = Column(String(30), nullable=False, default='lead_collaborator')
    created_by = Column(String(80), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    last_login_at = Column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("role = 'lead_collaborator'", name='ck_lead_account_role'),)


class LeadSession(Base):
    __tablename__ = 'lead_sessions'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String(36), ForeignKey('lead_accounts.id'), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)


class Lead(Base):
    __tablename__ = 'leads'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    legacy_id = Column(String(100), unique=True)
    name = Column(String(300), nullable=False)
    type = Column(String(80), nullable=False)
    type_label = Column(String(150), nullable=False, default='')
    city = Column(String(150), nullable=False, default='')
    region = Column(String(150), nullable=False, default='')
    address = Column(String(300), nullable=False, default='')
    country = Column(String(80), nullable=False, default='CZ')
    postal_code = Column(String(20), nullable=False, default='')
    district = Column(String(150), nullable=False, default='')
    lat = Column(Float)
    lng = Column(Float)
    location_accuracy = Column(String(300), nullable=False, default='')
    cluster = Column(String(150), nullable=False, default='')
    plan = Column(String(80), nullable=False, default='ověřit')
    programs = Column(String(150), nullable=False, default='')
    catalog_programs = Column(Integer, nullable=False, default=0)
    booking = Column(String(500), nullable=False, default='')
    online = Column(String(150), nullable=False, default='')
    online_completion = Column(String(150), nullable=False, default='ověřit')
    activity = Column(String(150), nullable=False, default='')
    relationship = Column(String(150), nullable=False, default='')
    regularity = Column(String(300), nullable=False, default='')
    score = Column(Integer, nullable=False, default=0)
    why = Column(Text, nullable=False, default='')
    catalog = Column(String(150), nullable=False, default='')
    catalog_role = Column(String(300), nullable=False, default='')
    website_url = Column(String(2000), nullable=False, default='')
    program_url = Column(String(2000), nullable=False, default='')
    stage = Column(String(100), nullable=False, default='Dosud neosloveno', index=True)
    result_reason = Column(Text, nullable=False, default='')
    next_action = Column(Text, nullable=False, default='')
    next_action_date = Column(Date, index=True)
    last_contact = Column(Date)
    internal_note = Column(Text, nullable=False, default='')
    assignee_id = Column(String(36), ForeignKey('lead_accounts.id'), index=True)
    archived = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=now)
    updated_by = Column(String(80), nullable=False)
    legacy_snapshot = Column(JSON)  # Private source provenance; never included in API/export.
    __table_args__ = (
        CheckConstraint('score BETWEEN 0 AND 100', name='ck_lead_score'),
        CheckConstraint('catalog_programs >= 0', name='ck_lead_program_count'),
        CheckConstraint('lat BETWEEN -90 AND 90', name='ck_lead_lat'),
        CheckConstraint('lng BETWEEN -180 AND 180', name='ck_lead_lng'),
    )


class LeadContact(Base):
    __tablename__ = 'lead_contacts'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey('leads.id'), nullable=False, index=True)
    first_name = Column(String(100), nullable=False, default='')
    last_name = Column(String(150), nullable=False, default='')
    position = Column(String(300), nullable=False, default='')
    email = Column(String(254), nullable=False, default='')
    phone = Column(String(80), nullable=False, default='')
    note = Column(Text, nullable=False, default='')
    primary = Column(Boolean, nullable=False, default=False)
    __table_args__ = (Index('uq_lead_primary_contact', 'lead_id', unique=True,
                           postgresql_where=primary.is_(True), sqlite_where=primary.is_(True)),)


class LeadActivity(Base):
    __tablename__ = 'lead_activities'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey('leads.id'), nullable=False, index=True)
    kind = Column(String(30), nullable=False)
    subject = Column(String(300), nullable=False)
    body = Column(Text, nullable=False, default='')
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=now)
    actor_id = Column(String(80), nullable=False)
    actor_name = Column(String(220), nullable=False)


class LeadAudit(Base):
    __tablename__ = 'lead_audit'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey('leads.id'), index=True)
    entity = Column(String(30), nullable=False)
    entity_id = Column(String(100), nullable=False)
    actor_id = Column(String(80), nullable=False)
    actor_name = Column(String(220), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=now)
    action = Column(String(30), nullable=False)
    field = Column(String(80), nullable=False)
    old_value = Column(JSON)
    new_value = Column(JSON)


class LeadGoal(Base):
    __tablename__ = 'lead_goals'
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    metric = Column(String(30), nullable=False)
    target = Column(Integer, nullable=False)
    deadline = Column(Date, nullable=False)
    cluster = Column(String(150))
    __table_args__ = (CheckConstraint('target > 0', name='ck_lead_goal_target'),)
