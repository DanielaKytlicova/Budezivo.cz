import csv
import io
from datetime import date, datetime
from sqlalchemy import select, or_, exists
from fastapi import HTTPException
from database.lead_models import Lead, LeadAccount, LeadContact, LeadAudit
from models.lead_schemas import ContactInput


def scalar(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def row_dict(row):
    return {c.name: scalar(getattr(row, c.name)) for c in row.__table__.columns
            if c.name not in ('password_hash', 'token_hash', 'legacy_snapshot')}


def record_changes(db, actor, entity, entity_id, before, after, lead_id=None, action='update'):
    for field in sorted(set(before) | set(after)):
        if field in ('password', 'password_hash', 'token_hash', 'legacy_snapshot'):
            continue
        old, new = scalar(before.get(field)), scalar(after.get(field))
        if old != new:
            db.add(LeadAudit(lead_id=lead_id, entity=entity, entity_id=entity_id,
                             actor_id=actor['actor_id'], actor_name=actor['name'], action=action,
                             field=field, old_value=old, new_value=new))


async def check_assignee(db, assignee_id):
    if assignee_id:
        account = await db.get(LeadAccount, assignee_id)
        if not account or not account.active:
            raise HTTPException(422, 'Vyberte aktivního spolupracovníka')


def filtered_query(actor, q='', type='', region='', cluster='', plan='', stage='',
                   connected=False, mine=False, assignee='', due='', archived=False):
    query = select(Lead).where(Lead.archived == archived)
    for key, value in [('type', type), ('region', region), ('cluster', cluster), ('stage', stage)]:
        if value:
            query = query.where(getattr(Lead, key) == value)
    if plan:
        if plan == 'FREE':
            query = query.where(Lead.plan.in_(['FREE', 'FREE – ověřit', 'FREE – podmíněně', 'FREE – pobočka']))
        elif plan == 'PRO':
            query = query.where(Lead.plan.in_(['PRO', 'PRO – podle provozu']))
        else:
            query = query.where(Lead.plan == plan)
    if connected:
        query = query.where(Lead.stage.startswith('Připojeno'))
    if mine:
        query = query.where(Lead.assignee_id == actor['id'])
    if assignee:
        query = query.where(Lead.assignee_id.is_(None) if assignee == 'unassigned' else Lead.assignee_id == assignee)
    if due == 'overdue':
        query = query.where(Lead.next_action_date < date.today())
    elif due == 'today':
        query = query.where(Lead.next_action_date == date.today())
    elif due == 'planned':
        query = query.where(Lead.next_action_date.is_not(None))
    elif due:
        raise HTTPException(422, 'Neznámý filtr termínu')
    if q:
        pattern = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        contact = exists(select(LeadContact.id).where(LeadContact.lead_id == Lead.id, or_(
            *[getattr(LeadContact, key).ilike(pattern, escape='\\')
              for key in ('first_name', 'last_name', 'email', 'phone', 'position')])))
        query = query.where(or_(Lead.name.ilike(pattern, escape='\\'), Lead.city.ilike(pattern, escape='\\'), contact))
    return query.order_by(Lead.name, Lead.id)


async def contact_for(db, lead_id):
    return (await db.execute(select(LeadContact).where(LeadContact.lead_id == lead_id, LeadContact.primary.is_(True)))).scalar_one_or_none()


async def save_contact(db, lead_id, data, actor):
    contact = await contact_for(db, lead_id)
    before = {key: getattr(contact, key) for key in ContactInput.model_fields} if contact else {}
    if not contact:
        contact = LeadContact(lead_id=lead_id, primary=True)
        db.add(contact)
    for key, value in data.items():
        setattr(contact, key, value)
    await db.flush()
    record_changes(db, actor, 'contact', contact.id, before, data, lead_id)


def safe_csv_cell(value):
    value = '' if value is None else str(value)
    # Excel/LibreOffice formula injection, including leading whitespace/control characters.
    if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')):
        return "'" + value
    return value


def csv_export(rows):
    output = io.StringIO(newline='')
    fields = [c.name for c in Lead.__table__.columns if c.name != 'legacy_snapshot']
    fields += ['contact_first_name', 'contact_last_name', 'contact_position', 'contact_email', 'contact_phone', 'contact_note']
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: safe_csv_cell(value) for key, value in row.items()})
    return '\ufeff' + output.getvalue()
