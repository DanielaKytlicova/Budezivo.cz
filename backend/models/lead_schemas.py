"""Bounded inputs shared by API and source migration."""
import re
from datetime import date, datetime
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

STAGES = ['Dosud neosloveno', 'Výzkum / ověřit', 'Připraveno k oslovení',
          'Osloveno – čekáme na odpověď', 'Kontakt navázán / probíhá jednání',
          'Rozhodnutí odloženo', 'Odmítli', 'Souhlas / onboarding',
          'Připojeno – nastavuje programy', 'Připojeno – aktivně používá',
          'Připojeno – platící', 'Neobchodní / pouze katalog']
PLANS = ['FREE', 'FREE – ověřit', 'FREE – podmíněně', 'FREE – pobočka', 'PRO', 'PRO+', 'PRO – podle provozu', 'ověřit']


class StrictInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_max_length=10000)


class ContactInput(StrictInput):
    first_name: str = Field(default='', max_length=100)
    last_name: str = Field(default='', max_length=150)
    position: str = Field(default='', max_length=300)
    email: str = Field(default='', max_length=254)
    phone: str = Field(default='', max_length=80)
    note: str = Field(default='', max_length=5000)

    @field_validator('email')
    @classmethod
    def email_valid(cls, value):
        if value and any(not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email.strip()) for email in value.split(';')):
            raise ValueError('Neplatný pracovní e-mail')
        return value


class LeadInput(StrictInput):
    name: str = Field(min_length=1, max_length=300)
    type: str = Field(min_length=1, max_length=80)
    type_label: str = Field(default='', max_length=150)
    city: str = Field(default='', max_length=150)
    region: str = Field(default='', max_length=150)
    address: str = Field(default='', max_length=300)
    country: str = Field(default='CZ', max_length=80)
    postal_code: str = Field(default='', max_length=20)
    district: str = Field(default='', max_length=150)
    lat: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    lng: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    location_accuracy: str = Field(default='', max_length=300)
    cluster: str = Field(default='', max_length=150)
    plan: str = 'ověřit'
    programs: str = Field(default='', max_length=150)
    catalog_programs: int = Field(default=0, ge=0, le=100000)
    booking: str = Field(default='', max_length=500)
    online: str = Field(default='', max_length=150)
    online_completion: str = Field(default='ověřit', max_length=150)
    activity: str = Field(default='', max_length=150)
    relationship: str = Field(default='', max_length=150)
    regularity: str = Field(default='', max_length=300)
    score: int = Field(default=0, ge=0, le=100)
    why: str = Field(default='', max_length=10000)
    catalog: str = Field(default='', max_length=150)
    catalog_role: str = Field(default='', max_length=300)
    website_url: str = Field(default='', max_length=2000)
    program_url: str = Field(default='', max_length=2000)
    stage: str = STAGES[0]
    result_reason: str = Field(default='', max_length=10000)
    next_action: str = Field(default='', max_length=5000)
    next_action_date: date | None = None
    last_contact: date | None = None
    internal_note: str = Field(default='', max_length=10000)
    assignee_id: str | None = Field(default=None, max_length=36)
    archived: bool = False
    contact: ContactInput = Field(default_factory=ContactInput)

    @field_validator('stage')
    @classmethod
    def valid_stage(cls, value):
        if value not in STAGES:
            raise ValueError('Neznámý stav')
        return value

    @field_validator('plan')
    @classmethod
    def valid_plan(cls, value):
        if value not in PLANS:
            raise ValueError('Neznámý tarif')
        return value

    @field_validator('website_url', 'program_url')
    @classmethod
    def safe_url(cls, value):
        parsed = urlsplit(value)
        if value and (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password):
            raise ValueError('URL musí být veřejná http/https adresa bez přihlašovacích údajů')
        return value

    @model_validator(mode='after')
    def paired_coordinates(self):
        if (self.lat is None) != (self.lng is None):
            raise ValueError('Vyplňte obě souřadnice')
        return self


class LeadUpdate(StrictInput):
    version: int = Field(ge=1)
    changes: dict


class ActivityInput(StrictInput):
    kind: Literal['email', 'phone', 'meeting', 'note', 'status', 'other']
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(default='', max_length=10000)
    occurred_at: datetime

    @field_validator('occurred_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Datum musí obsahovat časové pásmo')
        return value


class AccountInput(StrictInput):
    username: str = Field(min_length=3, max_length=80, pattern=r'^[a-zA-Z0-9._-]+$')
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    active: bool = True
    password: str | None = Field(default=None, min_length=12, max_length=72)

    @field_validator('username')
    @classmethod
    def normalized(cls, value):
        return value.lower()

    @field_validator('password')
    @classmethod
    def bcrypt_limit(cls, value):
        if value is not None and len(value.encode('utf-8')) > 72:
            raise ValueError('Heslo může mít nejvýše 72 UTF-8 bajtů')
        return value


class LoginInput(StrictInput):
    username: str = Field(max_length=80)
    password: str = Field(max_length=200)


class GoalInput(StrictInput):
    name: str = Field(min_length=1, max_length=200)
    metric: Literal['connected', 'paying', 'programs']
    target: int = Field(gt=0, le=1000000)
    deadline: date
    cluster: str | None = Field(default=None, max_length=150)


class AssignmentInput(StrictInput):
    lead_ids: list[str] = Field(min_length=1, max_length=500)
    assignee_id: str | None = Field(default=None, max_length=36)
