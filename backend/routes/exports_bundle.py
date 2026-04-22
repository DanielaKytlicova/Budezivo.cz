"""
Bulk exports — download all generated files as a single ZIP bundle.
Gated: PRO / PRO+ / Superadmin only. Scoped to the caller's institution.
"""
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    InstitutionRepositorySupabase,
    ProgramRepositorySupabase,
)
from services.plan_service import has_feature_access

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/exports", tags=["Exports"])

SUPERADMIN_EMAILS = ["demo@budezivo.cz", "admin@budezivo.cz"]


async def _authorize(db: AsyncSession, user: dict) -> None:
    # Superadmin always allowed
    if user.get("email") in SUPERADMIN_EMAILS:
        return
    # Regular users: must be admin/spravce AND on a PRO/PRO+ plan
    if user.get("role") not in ("admin", "spravce"):
        raise HTTPException(
            status_code=403,
            detail="Hromadný export mohou stahovat pouze administrátoři instituce.",
        )
    inst = await InstitutionRepositorySupabase(db).find_by_id(user["institution_id"])
    plan = (inst or {}).get("plan", "free")
    plan_status = (inst or {}).get("plan_status", "active")
    if not has_feature_access(plan, plan_status, "data_export"):
        raise HTTPException(
            status_code=403,
            detail="Hromadný export je dostupný pouze pro plány PRO a PRO+. Upgradujte v Profilu → Plán.",
        )


@router.get("/download-bundle")
async def download_export_bundle(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zip all exports the system generates for the caller's institution."""
    await _authorize(db, current_user)

    institution_id = current_user["institution_id"]
    inst_repo = InstitutionRepositorySupabase(db)
    institution = await inst_repo.find_by_id(institution_id)
    inst_name = (institution or {}).get("name", "instituce")
    safe_inst = "".join(c if c.isalnum() else "_" for c in inst_name)[:40]

    # Lazy imports so circular imports are avoided
    from routes.schools import export_schools_csv, download_import_template
    from routes.feedback import export_feedback_csv
    from routes.statistics import export_statistics_csv
    from routes.gdpr import export_personal_data
    from routes.calendar_export import (
        generate_feed_token, institution_calendar_feed, program_calendar_feed,
    )
    from routes.programs import get_archive_report

    buf = io.BytesIO()
    manifest: list[dict] = []

    async def _bytes_from_call(coro_or_result, filename: str):
        from starlette.responses import StreamingResponse
        try:
            result = await coro_or_result if hasattr(coro_or_result, "__await__") else coro_or_result
            if isinstance(result, StreamingResponse):
                chunks = []
                async for chunk in result.body_iterator:
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    chunks.append(chunk)
                data = b"".join(chunks)
                ct = result.media_type or "application/octet-stream"
            elif isinstance(result, Response):
                data = result.body
                ct = result.media_type or result.headers.get("content-type", "application/octet-stream")
            elif isinstance(result, (bytes, bytearray)):
                data = bytes(result)
                ct = "application/octet-stream"
            else:
                data = json.dumps(result, ensure_ascii=False, default=str, indent=2).encode("utf-8")
                ct = "application/json"
            manifest.append({"file": filename, "bytes": len(data), "content_type": ct})
            return data
        except HTTPException as he:
            manifest.append({"file": filename, "error": f"{he.status_code} {he.detail}"})
            return None
        except Exception as e:
            logger.exception("Export failed for %s", filename)
            manifest.append({"file": filename, "error": str(e)[:200]})
            return None

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        async def add(filename, coro):
            data = await _bytes_from_call(coro, filename)
            if data is not None:
                zf.writestr(filename, data)

        # 1) Schools CSV + import template (template takes no auth / no db)
        await add("01_skoly_kontakty.csv", export_schools_csv(current_user=current_user, db=db))
        await add("02_import_template_skol.xlsx", download_import_template())

        # 3) Feedback CSV
        await add("03_zpetna_vazba.csv",
                  export_feedback_csv(program_id=None, date_from=None, date_to=None,
                                      current_user=current_user, db=db))

        # 4-6) Statistics (CSV) — reservations / summary / programs
        common_stats = dict(period_type="month", year=None, month=None, semester=None,
                            start_date=None, end_date=None,
                            current_user=current_user, db=db)
        await add("04_statistiky_rezervace.csv",
                  export_statistics_csv(export_type="reservations", **common_stats))
        await add("05_statistiky_souhrn.csv",
                  export_statistics_csv(export_type="summary", **common_stats))
        await add("06_statistiky_programy.csv",
                  export_statistics_csv(export_type="programs", **common_stats))

        # 7) GDPR export — PDF + JSON side-by-side (GDPR Art. 20 compliance)
        try:
            raw_gdpr = await export_personal_data(format="json", current_user=current_user, db=db)
            from services.export_service import build_gdpr_export_pdf
            gdpr_pdf = build_gdpr_export_pdf(raw_gdpr)
            zf.writestr("07_gdpr_export.json",
                        json.dumps(raw_gdpr, ensure_ascii=False, default=str, indent=2).encode("utf-8"))
            zf.writestr("07_gdpr_export.pdf", gdpr_pdf)
            manifest.append({"file": "07_gdpr_export.json", "bytes": 0, "content_type": "application/json"})
            manifest.append({"file": "07_gdpr_export.pdf", "bytes": len(gdpr_pdf), "content_type": "application/pdf"})
        except Exception as e:
            logger.exception("GDPR export failed")
            manifest.append({"file": "07_gdpr_export", "error": str(e)[:200]})

        # 8) ICS — institution (needs HMAC token; pass status=None to bypass Query default)
        tk = await generate_feed_token(entity_type="institution", entity_id=institution_id,
                                       current_user=current_user)
        tok_val = tk.get("token") if isinstance(tk, dict) else None
        if tok_val:
            await add("08_kalendar_instituce.ics",
                      institution_calendar_feed(institution_id=institution_id,
                                                token=tok_val, status=None, db=db))

        # 9) Per-program ICS + archive report (cap 20 to bound bundle size)
        programs = await ProgramRepositorySupabase(db).find_by_institution(institution_id)
        for p in programs[:20]:
            pid = p["id"]
            safe = "".join(c if c.isalnum() else "_" for c in (p.get("name_cs") or pid))[:40]
            ptk = await generate_feed_token(entity_type="program", entity_id=pid,
                                            current_user=current_user)
            ptok_val = ptk.get("token") if isinstance(ptk, dict) else None
            if ptok_val:
                await add(f"09_kalendar_program_{safe}.ics",
                          program_calendar_feed(program_id=pid, token=ptok_val, db=db))
            await add(f"10_archive_report_{safe}.pdf",
                      get_archive_report(program_id=pid, format="pdf",
                                         current_user=current_user, db=db))

        # Manifest
        zf.writestr("MANIFEST.json", json.dumps({
            "institution_id": institution_id,
            "institution_name": inst_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files": manifest,
        }, ensure_ascii=False, indent=2))

    payload = buf.getvalue()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    # ASCII-only fallback + RFC 5987 UTF-8 encoded filename (Content-Disposition requires latin-1)
    from urllib.parse import quote
    ascii_inst = "".join(c if c.isascii() and c.isalnum() else "_" for c in inst_name)[:40] or "instituce"
    ascii_fn = f"budezivo_export_{ascii_inst}_{stamp}.zip"
    utf8_fn = f"budezivo_export_{safe_inst}_{stamp}.zip"

    return Response(
        content=payload,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_fn}"; filename*=UTF-8\'\'{quote(utf8_fn)}',
            "Cache-Control": "no-store",
        },
    )
