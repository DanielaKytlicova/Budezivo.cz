"""Reuse platform cryptography; CRM tokens cannot enter tenant admin APIs."""
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import JWT_SECRET, JWT_ALGORITHM
from core.security import decode_jwt_token, hash_refresh_token, generate_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES
from database.supabase import get_db
from database.models import User
from database.lead_models import LeadAccount, LeadSession
from routes.superadmin import SUPERADMIN_EMAILS


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def profile(account):
    return {'id': account.id, 'actor_id': 'lead:' + account.id,
            'name': f'{account.first_name} {account.last_name}',
            'username': account.username, 'role': 'lead_collaborator', 'superadmin': False}


def access_token(account, session):
    return jwt.encode({'user_id': account.id, 'account_type': 'leads',
                       'role': 'lead_collaborator', 'sid': session.id,
                       'exp': datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)},
                      JWT_SECRET, algorithm=JWT_ALGORITHM)


async def issue_session(db, account):
    raw = generate_refresh_token()
    session = LeadSession(account_id=account.id, token_hash=hash_refresh_token(raw),
                          expires_at=datetime.now(timezone.utc) + timedelta(hours=8))
    db.add(session)
    await db.flush()
    return {'token': access_token(account, session), 'refresh_token': raw, 'user': profile(account)}


async def require_leads(request: Request, db: AsyncSession = Depends(get_db)):
    # Prefer the explicit CRM bearer to an unrelated institution cookie.
    authorization = request.headers.get('authorization', '')
    token = authorization[7:] if authorization.startswith('Bearer ') else request.cookies.get('access_token', '')
    try:
        payload = decode_jwt_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(401, 'Přihlášení vyžadováno')
    if payload.get('impersonated_by_email') or payload.get('type'):
        raise HTTPException(403, 'Interní CRM není dostupné při impersonaci')
    if payload.get('account_type') == 'leads':
        account = await db.get(LeadAccount, payload.get('user_id', ''))
        session = await db.get(LeadSession, payload.get('sid', ''))
        if (not account or not account.active or not session or session.account_id != account.id
                or utc(session.expires_at) <= datetime.now(timezone.utc)):
            raise HTTPException(401, 'Relace již není platná')
        return {**profile(account), 'session_id': session.id}
    if payload.get('account_type') not in (None, 'admin'):
        raise HTTPException(403, 'Přístup pouze pro interní tým')
    try:
        user_id = uuid.UUID(payload.get('user_id', ''))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(401, 'Neplatná relace')
    user = await db.get(User, user_id)
    if (not user or user.email not in SUPERADMIN_EMAILS or user.status != 'active' or user.deleted_at):
        raise HTTPException(403, 'Přístup pouze pro interní tým')
    return {'id': str(user.id), 'actor_id': 'user:' + str(user.id), 'name': user.name or user.email,
            'superadmin': True, 'role': 'superadmin'}


async def require_lead_admin(actor=Depends(require_leads)):
    if not actor['superadmin']:
        raise HTTPException(403, 'Pouze superadmin')
    return actor


def require_edit(lead, actor):
    if not actor['superadmin'] and (lead.assignee_id != actor['id'] or lead.archived):
        raise HTTPException(403, 'Upravovat můžete pouze své aktivní leady')
