"""Validate and import an explicit complete seed + D1 export. No source fetch or deletion.

Dry run by default. --apply requires a database and imports atomically. Re-running
identical data is a no-op; changed source after any import is refused (no silent
CRM overwrite). Private exports must stay outside Git.
"""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models.lead_schemas import LeadInput

ALIASES = {'typeLabel': 'type_label', 'catalogRole': 'catalog_role', 'internalNote': 'internal_note',
           'lastContact': 'last_contact', 'nextActionDate': 'next_action_date', 'resultReason': 'result_reason',
           'locationAccuracy': 'location_accuracy', 'next': 'next_action', 'url': 'program_url'}
OVERRIDE_ALIASES = {'contact_name': 'contact', 'contact_role': 'position', 'next_action': 'next',
                    'program_url': 'url', 'catalog_role': 'catalogRole', 'last_contact': 'lastContact',
                    'next_action_date': 'nextActionDate', 'result_reason': 'resultReason',
                    'internal_note': 'internalNote'}


def prepare(seed, export):
    if not isinstance(seed, list) or not seed:
        raise ValueError('Prázdný nebo neplatný základní export')
    if not isinstance(export, dict) or export.get('has_more') is not False:
        raise ValueError('D1 export musí explicitně potvrdit has_more=false')
    projection = export.get('model_projection', {})
    if not projection or any(projection.get(k) for k in ('truncated', 'truncated_values', 'omitted_columns', 'omitted_rows', 'next_offset')):
        raise ValueError('D1 export je neúplný nebo krácený')
    overrides = export.get('rows')
    if not isinstance(overrides, list):
        raise ValueError('Chybí D1 rows')
    ids = [r['id'] for r in seed]
    override_ids = [r['institution_id'] for r in overrides]
    if len(set(ids)) != len(ids) or len(set(override_ids)) != len(override_ids):
        raise ValueError('Duplicitní stabilní ID')
    if set(override_ids) - set(ids):
        raise ValueError('D1 obsahuje instituci chybějící v základních datech')
    by_id = {r['institution_id']: r for r in overrides}
    result = []
    for source in seed:
        legacy_id = source['id']
        if not isinstance(legacy_id, str) or not 1 <= len(legacy_id) <= 100:
            raise ValueError('Neplatné legacy ID')
        override = by_id.get(legacy_id, {})
        merged = dict(source)
        for key, value in override.items():
            target = OVERRIDE_ALIASES.get(key, key)
            if key in ('institution_id', 'updated_at', 'updated_by'):
                continue
            # Original application uses null coalescing for these four aliases.
            if key in ('contact_name', 'contact_role', 'next_action', 'program_url') and value is None:
                continue
            merged[target] = value
        values = {ALIASES.get(k, k): v for k, v in merged.items()
                  if ALIASES.get(k, k) in LeadInput.model_fields}
        for key in ('next_action_date', 'last_contact'):
            values[key] = values.get(key) or None
        name = str(merged.get('contact') or '')
        first, _, last = name.partition(' ')
        values['contact'] = {'first_name': first, 'last_name': last, 'position': merged.get('position') or '',
                             'email': merged.get('email') or '', 'phone': merged.get('phone') or '', 'note': ''}
        # Explicit exact count only. Ranges/estimates remain preserved in programs.
        programs = str(values.get('programs') or '')
        values['catalog_programs'] = int(programs) if re.fullmatch(r'\d+', programs) else 0
        validated = LeadInput.model_validate(values).model_dump(mode='json')
        snapshot = {'base': source, 'override': override}
        result.append({'legacy_id': legacy_id, 'values': validated, 'snapshot': snapshot})
    return result


def summary(records):
    values = [r['values'] for r in records]
    return {'total': len(values), 'by_stage': dict(sorted(Counter(v['stage'] for v in values).items())),
            'connected': sum(v['stage'].startswith('Připojeno') for v in values),
            'paying': sum(v['stage'] == 'Připojeno – platící' for v in values),
            'internal_notes': sum(bool(v['internal_note']) for v in values),
            'contacts': sum(any(v['contact'].values()) for v in values),
            'checks': [{'legacy_id': r['legacy_id'], 'city': r['values']['city'], 'stage': r['values']['stage'],
                        'matches_source': True} for r in records if r['legacy_id'] in ('BZ-0001', 'BZ-0024', 'BZ-0026')]}


async def apply(records):
    from sqlalchemy import select
    from database.supabase import AsyncSessionLocal
    from database.lead_models import Lead
    from services.lead_service import save_contact, record_changes, contact_for
    actor = {'actor_id': 'migration:lead-map', 'name': 'Migrace původní Lead Map'}
    if AsyncSessionLocal is None:
        raise ValueError('DATABASE_URL není nastaveno')
    async with AsyncSessionLocal() as db:
        async with db.begin():
            # Transaction lock serializes importers without locking tenant tables.
            if db.bind.dialect.name == 'postgresql':
                from sqlalchemy import text
                await db.execute(text("SELECT pg_advisory_xact_lock(71942027)"))
            imported = 0
            for record in records:
                lead = (await db.execute(select(Lead).where(Lead.legacy_id == record['legacy_id']).with_for_update())).scalar_one_or_none()
                if lead:
                    if lead.legacy_snapshot != record['snapshot']:
                        raise ValueError('Zdroj se od předchozího importu změnil; vyžaduje vědomé sloučení')
                    continue
                import uuid
                data = LeadInput.model_validate(record['values'])
                values = data.model_dump(exclude={'contact'})
                lead = Lead(id=str(uuid.uuid4()), legacy_id=record['legacy_id'], **values,
                            updated_by=actor['actor_id'], legacy_snapshot=record['snapshot'])
                db.add(lead)
                await db.flush()
                record_changes(db, actor, 'lead', lead.id, {}, values, lead.id, 'import')
                await save_contact(db, lead.id, data.contact.model_dump(), actor)
                imported += 1
            await db.flush()
            verified = []
            for record in records:
                lead = (await db.execute(select(Lead).where(Lead.legacy_id == record['legacy_id']))).scalar_one()
                contact = await contact_for(db, lead.id)
                values = {k: getattr(lead, k) for k in LeadInput.model_fields if k != 'contact'}
                values['contact'] = {k: getattr(contact, k) for k in record['values']['contact']}
                normalized = LeadInput.model_validate(values).model_dump(mode='json')
                if normalized != record['values']:
                    raise ValueError('CRM již obsahuje novější úpravy; úplná shoda se zdrojem není potvrzena')
                verified.append({**record, 'values': normalized})
            if summary(verified) != summary(records):
                raise ValueError('Kontrolní počty nesouhlasí; transakce se vrací zpět')
        return {'inserted': imported, 'database_verified': True, 'comparison': summary(verified)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', required=True, type=Path)
    parser.add_argument('--overrides', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        seed = json.loads(args.seed.read_text())
        overrides = json.loads(args.overrides.read_text())
        records = prepare(seed, overrides)
        report = {'mode': 'apply' if args.apply else 'dry-run', 'database_verified': False,
                  'source_sha256': hashlib.sha256(args.seed.read_bytes() + args.overrides.read_bytes()).hexdigest(),
                  'overrides': len(overrides['rows']), 'comparison': summary(records)}
        if args.apply:
            report.update(asyncio.run(apply(records)))
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except Exception as exc:
        # Exception text may contain source PII or database DSNs. Keep logs bounded.
        print(f'Import nebyl dokončen ({type(exc).__name__}); databázové změny nebyly potvrzeny.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
