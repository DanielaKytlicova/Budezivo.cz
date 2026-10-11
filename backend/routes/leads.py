"""Internal CRM API. Every read/write is server-authorized; no public data URLs."""
from datetime import datetime, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError, Field
from sqlalchemy import select, delete, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from core.security import hash_password, verify_password, hash_refresh_token, generate_refresh_token
from database.supabase import get_db
from database.lead_models import Lead, LeadAccount, LeadSession, LeadContact, LeadActivity, LeadAudit, LeadGoal
from models.lead_schemas import (StrictInput, LoginInput, AccountInput, LeadInput, LeadUpdate,
                                 ActivityInput, GoalInput, AssignmentInput, STAGES, PLANS)
from services.lead_security import require_leads, require_lead_admin, require_edit, issue_session, access_token, profile, utc
from services.lead_service import row_dict, record_changes, filtered_query, check_assignee, contact_for, save_contact, csv_export
from services.lead_import import SpreadsheetInput, preview_import, apply_import

router = APIRouter(prefix='/leads', tags=['Internal CRM'])
limiter = Limiter(key_func=get_remote_address)
# Equal-cost password verification for unknown accounts; never exposed or logged.
DUMMY_HASH = hash_password('not-a-real-account-password')


async def commit(db):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, 'Záznam s tímto identifikátorem již existuje')


@router.post('/auth/login')
@limiter.limit('5/minute')
async def login(request: Request, data: LoginInput, db: AsyncSession = Depends(get_db)):
    account = (await db.execute(select(LeadAccount).where(LeadAccount.username == data.username.strip().lower()))).scalar_one_or_none()
    try:
        valid = verify_password(data.password, account.password_hash if account else DUMMY_HASH)
    except ValueError:
        valid = False
    if not valid or not account or not account.active:
        raise HTTPException(401, 'Nesprávné uživatelské jméno nebo heslo')
    account.last_login_at = datetime.now(timezone.utc)
    result = await issue_session(db, account)
    await commit(db)
    return result


class RefreshInput(StrictInput):
    refresh_token: str = Field(min_length=20, max_length=200)


@router.post('/auth/refresh')
@limiter.limit('20/minute')
async def refresh(request: Request, data: RefreshInput, db: AsyncSession = Depends(get_db)):
    session = (await db.execute(select(LeadSession).where(LeadSession.token_hash == hash_refresh_token(data.refresh_token)).with_for_update())).scalar_one_or_none()
    account = await db.get(LeadAccount, session.account_id) if session else None
    if not session or not account or not account.active or utc(session.expires_at) <= datetime.now(timezone.utc):
        raise HTTPException(401, 'Relace vypršela, přihlaste se znovu')
    raw = generate_refresh_token()
    session.token_hash = hash_refresh_token(raw)
    result = {'token': access_token(account, session), 'refresh_token': raw, 'user': profile(account)}
    await commit(db)
    return result


@router.post('/auth/logout')
async def logout(actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    if actor.get('session_id'):
        await db.execute(delete(LeadSession).where(LeadSession.id == actor['session_id']))
        await commit(db)
    return {'ok': True}


@router.get('/me')
async def me(actor=Depends(require_leads)):
    return {k: v for k, v in actor.items() if k != 'session_id'}


@router.get('/metadata')
async def metadata(actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    options = {}
    for key in ('type', 'region', 'cluster'):
        values = (await db.execute(select(getattr(Lead, key)).where(Lead.archived.is_(False)).distinct())).scalars().all()
        options[key] = sorted(v for v in values if v)
    accounts = (await db.execute(select(LeadAccount).order_by(LeadAccount.last_name))).scalars().all()
    return {**options, 'stages': STAGES, 'plans': PLANS,
            'accounts': [{'id': a.id, 'name': f'{a.first_name} {a.last_name}', 'active': a.active} for a in accounts]}


async def filters(q: str = Query('', max_length=200), type: str = Query('', max_length=80),
                  region: str = Query('', max_length=150), cluster: str = Query('', max_length=150),
                  plan: str = Query('', max_length=80), stage: str = Query('', max_length=100),
                  connected: bool = False, mine: bool = False, assignee: str = Query('', max_length=40),
                  due: str = Query('', max_length=20), archived: bool = False):
    return locals()


@router.get('')
async def list_leads(actor=Depends(require_leads), f=Depends(filters), db: AsyncSession = Depends(get_db),
                     offset: int = Query(0, ge=0), limit: int = Query(500, ge=1, le=500)):
    query = filtered_query(actor, **f)
    count = await db.scalar(select(func.count()).select_from(query.subquery()))
    leads = (await db.execute(query.offset(offset).limit(limit))).scalars().all()
    return {'items': [row_dict(lead) for lead in leads], 'total': count}


@router.get('/export')
async def export(actor=Depends(require_lead_admin), f=Depends(filters), db: AsyncSession = Depends(get_db)):
    leads = (await db.execute(filtered_query(actor, **f))).scalars().all()
    contacts = (await db.execute(select(LeadContact).where(LeadContact.primary.is_(True)))).scalars().all()
    by_id = {c.lead_id: c for c in contacts}
    rows = []
    for lead in leads:
        row = row_dict(lead)
        contact = by_id.get(lead.id)
        if contact:
            row.update({'contact_' + key: getattr(contact, key) for key in ('first_name', 'last_name', 'position', 'email', 'phone', 'note')})
        rows.append(row)
    return Response(csv_export(rows), media_type='text/csv; charset=utf-8', headers={
        'Content-Disposition': 'attachment; filename="budezivo-leady.csv"', 'Cache-Control': 'no-store'})


@router.get('/team')
async def team(actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    accounts = (await db.execute(select(LeadAccount).order_by(LeadAccount.username))).scalars().all()
    counts = dict((await db.execute(select(Lead.assignee_id, func.count()).where(Lead.archived.is_(False)).group_by(Lead.assignee_id))).all())
    return [{**row_dict(a), 'assigned_count': counts.get(a.id, 0)} for a in accounts]


@router.post('/import/preview')
@limiter.limit('20/minute')
async def import_preview(request: Request, data: SpreadsheetInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    report, _ = await preview_import(db, data)
    return report


@router.post('/import')
@limiter.limit('10/minute')
async def import_spreadsheet(request: Request, data: SpreadsheetInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    report = await apply_import(db, data, actor)
    await commit(db)
    return report


@router.post('/team', status_code=201)
async def create_account(data: AccountInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    if not data.password:
        raise HTTPException(422, 'Vyplňte počáteční heslo (alespoň 12 znaků)')
    account = LeadAccount(id=str(uuid.uuid4()), **data.model_dump(exclude={'password'}),
                          password_hash=hash_password(data.password), created_by=actor['actor_id'])
    db.add(account)
    record_changes(db, actor, 'account', account.id, {}, data.model_dump(exclude={'password'}), action='create')
    await commit(db)
    return row_dict(account)


@router.put('/team/{account_id}')
async def update_account(account_id: str, data: AccountInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    account = (await db.execute(select(LeadAccount).where(LeadAccount.id == account_id).with_for_update())).scalar_one_or_none()
    if not account:
        raise HTTPException(404, 'Účet nenalezen')
    changes = data.model_dump(exclude={'password'})
    record_changes(db, actor, 'account', account.id, {key: getattr(account, key) for key in changes}, changes)
    for key, value in changes.items():
        setattr(account, key, value)
    if data.password:
        account.password_hash = hash_password(data.password)
        record_changes(db, actor, 'account', account.id, {}, {'credentials_reset': True}, action='reset')
    if data.password or not data.active:
        await db.execute(delete(LeadSession).where(LeadSession.account_id == account.id))
    await commit(db)
    return row_dict(account)


@router.post('/assign')
async def assign(data: AssignmentInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    await check_assignee(db, data.assignee_id)
    leads = (await db.execute(select(Lead).where(Lead.id.in_(data.lead_ids)).order_by(Lead.id).with_for_update())).scalars().all()
    if len(leads) != len(set(data.lead_ids)):
        raise HTTPException(404, 'Některý lead nebyl nalezen; nic nebylo přeřazeno')
    for lead in leads:
        if lead.assignee_id != data.assignee_id:
            record_changes(db, actor, 'lead', lead.id, {'assignee_id': lead.assignee_id}, {'assignee_id': data.assignee_id}, lead.id)
            lead.assignee_id = data.assignee_id
            lead.version += 1
            lead.updated_at = datetime.now(timezone.utc)
            lead.updated_by = actor['actor_id']
    await commit(db)
    return {'updated': len(leads)}


@router.get('/goals')
async def goals(actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    goals = (await db.execute(select(LeadGoal).order_by(LeadGoal.name))).scalars().all()
    result = []
    for goal in goals:
        metric = func.sum(Lead.catalog_programs) if goal.metric == 'programs' else func.count(Lead.id)
        query = select(metric).where(Lead.archived.is_(False), Lead.stage.startswith('Připojeno'))
        if goal.metric == 'paying':
            query = query.where(Lead.stage == STAGES[10])
        if goal.cluster:
            query = query.where(Lead.cluster == goal.cluster)
        value = (await db.scalar(query)) or 0
        result.append({**row_dict(goal), 'current': value, 'percent': round(value / goal.target * 100)})
    return result


@router.post('/goals', status_code=201)
async def create_goal(data: GoalInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    goal = LeadGoal(id=str(uuid.uuid4()), **data.model_dump())
    db.add(goal)
    record_changes(db, actor, 'goal', goal.id, {}, data.model_dump(), action='create')
    await commit(db)
    return row_dict(goal)


@router.put('/goals/{goal_id}')
async def update_goal(goal_id: str, data: GoalInput, actor=Depends(require_lead_admin), db: AsyncSession = Depends(get_db)):
    goal = (await db.execute(select(LeadGoal).where(LeadGoal.id == goal_id).with_for_update())).scalar_one_or_none()
    if not goal:
        raise HTTPException(404, 'Cíl nenalezen')
    changes = data.model_dump()
    record_changes(db, actor, 'goal', goal.id, {k: getattr(goal, k) for k in changes}, changes)
    for key, value in changes.items():
        setattr(goal, key, value)
    await commit(db)
    return row_dict(goal)


@router.post('', status_code=201)
async def create_lead(data: LeadInput, actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    values = data.model_dump(exclude={'contact'})
    if not actor['superadmin']:
        if data.assignee_id not in (None, actor['id']) or data.archived:
            raise HTTPException(403, 'Přiřazení jinému pracovníkovi a archivaci mění pouze superadmin')
        values['assignee_id'] = actor['id']
    await check_assignee(db, values['assignee_id'])
    lead = Lead(id=str(uuid.uuid4()), **values, updated_by=actor['actor_id'])
    db.add(lead)
    await db.flush()
    record_changes(db, actor, 'lead', lead.id, {}, values, lead.id, 'create')
    await save_contact(db, lead.id, data.contact.model_dump(), actor)
    await commit(db)
    return row_dict(lead)


async def get_lead(db, lead_id, lock=False):
    query = select(Lead).where(Lead.id == lead_id)
    if lock:
        query = query.with_for_update()
    lead = (await db.execute(query)).scalar_one_or_none()
    if not lead:
        raise HTTPException(404, 'Instituce nenalezena')
    return lead


@router.get('/{lead_id}')
async def detail(lead_id: str, actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    lead = await get_lead(db, lead_id)
    contacts = (await db.execute(select(LeadContact).where(LeadContact.lead_id == lead.id))).scalars().all()
    activities = (await db.execute(select(LeadActivity).where(LeadActivity.lead_id == lead.id).order_by(LeadActivity.occurred_at.desc()))).scalars().all()
    audit = (await db.execute(select(LeadAudit).where(LeadAudit.lead_id == lead.id).order_by(LeadAudit.occurred_at.desc(), LeadAudit.id))).scalars().all()
    return {**row_dict(lead), 'contacts': [row_dict(c) for c in contacts],
            'activities': [row_dict(a) for a in activities], 'audit': [row_dict(a) for a in audit],
            'can_edit': actor['superadmin'] or (lead.assignee_id == actor['id'] and not lead.archived)}


@router.patch('/{lead_id}')
async def update_lead(lead_id: str, data: LeadUpdate, actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    lead = await get_lead(db, lead_id, lock=True)
    require_edit(lead, actor)
    if data.version != lead.version:
        raise HTTPException(409, 'Instituci mezitím někdo upravil. Načtěte aktuální detail a změny zopakujte.')
    if not actor['superadmin'] and set(data.changes) & {'assignee_id', 'archived'}:
        raise HTTPException(403, 'Přiřazení a archivaci mění pouze superadmin')
    current_contact = await contact_for(db, lead.id)
    before = {k: getattr(lead, k) for k in LeadInput.model_fields if k != 'contact'}
    current = {**before, 'contact': {k: getattr(current_contact, k) for k in ('first_name', 'last_name', 'position', 'email', 'phone', 'note')} if current_contact else {}}
    try:
        validated = LeadInput.model_validate({**current, **data.changes})
    except ValidationError:
        # Do not echo invalid note/contact/password values into errors or logs.
        raise HTTPException(422, 'Neplatné hodnoty polí; zkontrolujte délky, URL, kontakty a souřadnice')
    if validated.assignee_id != lead.assignee_id:
        await check_assignee(db, validated.assignee_id)
    after = validated.model_dump(exclude={'contact'})
    record_changes(db, actor, 'lead', lead.id, before, after, lead.id)
    for key, value in after.items():
        setattr(lead, key, value)
    if 'contact' in data.changes:
        await save_contact(db, lead.id, validated.contact.model_dump(), actor)
    lead.version += 1
    lead.updated_at = datetime.now(timezone.utc)
    lead.updated_by = actor['actor_id']
    await commit(db)
    return row_dict(lead)


@router.post('/{lead_id}/activities', status_code=201)
async def add_activity(lead_id: str, data: ActivityInput, actor=Depends(require_leads), db: AsyncSession = Depends(get_db)):
    lead = await get_lead(db, lead_id, lock=True)
    require_edit(lead, actor)
    activity = LeadActivity(id=str(uuid.uuid4()), lead_id=lead.id, **data.model_dump(),
                            actor_id=actor['actor_id'], actor_name=actor['name'])
    db.add(activity)
    record_changes(db, actor, 'activity', activity.id, {}, data.model_dump(), lead.id, 'create')
    await commit(db)
    return row_dict(activity)
