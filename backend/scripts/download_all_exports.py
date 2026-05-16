"""Download ALL exports from Galerie demo account and save to /app/exports."""
import asyncio, os, json, zipfile, shutil
from datetime import datetime
import httpx

API = "https://school-crm-pilot.preview.emergentagent.com"
OUT = "/app/exports"
INST = "eefb9cbf-52bf-4e20-9418-5b2f659f8d23"

os.makedirs(OUT, exist_ok=True)
manifest = []


async def save(client, name, url, headers=None):
    try:
        r = await client.get(url, headers=headers, timeout=60.0)
        # Derive filename from Content-Disposition if present
        cd = r.headers.get("content-disposition", "")
        ext = ""
        if "filename=" in cd:
            ext = cd.split("filename=")[-1].strip('"; ').split(".")[-1]
        else:
            ct = r.headers.get("content-type", "")
            ext_map = {
                "text/csv": "csv",
                "application/json": "json",
                "text/calendar": "ics",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
                "application/pdf": "pdf",
            }
            ext = next((v for k, v in ext_map.items() if k in ct), "bin")
        path = f"{OUT}/{name}.{ext}"
        with open(path, "wb") as f:
            f.write(r.content)
        manifest.append({"name": name, "file": path, "bytes": len(r.content),
                         "status": r.status_code, "content_type": r.headers.get("content-type", "")})
        return r
    except Exception as e:
        manifest.append({"name": name, "error": str(e)})
        return None


async def main():
    # cleanup old files
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Login
        r = await client.post(f"{API}/api/auth/login",
                              json={"email": "galerie@budezivo.cz", "password": "Galerie2026!"})
        token = r.json().get("access_token") or r.json().get("token")
        H = {"Authorization": f"Bearer {token}"}

        # Get a program + a completed reservation for detail exports
        programs = (await client.get(f"{API}/api/programs", headers=H)).json()
        p0 = programs[0]

        # ── 1. Schools CSV export ──
        await save(client, "01_skoly_kontakty", f"{API}/api/schools/export-csv", H)

        # ── 2. Schools import template (XLSX) ──
        await save(client, "02_import_template_skol", f"{API}/api/schools/import-template", H)

        # ── 3. Feedback CSV ──
        await save(client, "03_zpetna_vazba", f"{API}/api/feedback/export", H)

        # ── 4. Statistics CSV (reservations) ──
        await save(client, "04_statistiky_rezervace", f"{API}/api/statistics/export/csv?export_type=reservations", H)
        # Also 'summary' and 'programs' variants
        await save(client, "05_statistiky_souhrn", f"{API}/api/statistics/export/csv?export_type=summary", H)
        await save(client, "06_statistiky_programy", f"{API}/api/statistics/export/csv?export_type=programs", H)

        # ── 5. GDPR export ──
        await save(client, "07_gdpr_export", f"{API}/api/gdpr/export", H)

        # ── 6. ICS feeds (HMAC-tokened) ──
        tk = (await client.get(f"{API}/api/calendar/feed-token/institution/{INST}", headers=H)).json().get("token")
        await save(client, "08_kalendar_instituce", f"{API}/api/calendar/institution/{INST}.ics?token={tk}")

        for p in programs[:3]:  # first 3 programs
            tk = (await client.get(f"{API}/api/calendar/feed-token/program/{p['id']}", headers=H)).json().get("token")
            safe = "".join(c if c.isalnum() else "_" for c in p["name_cs"][:30])
            await save(client, f"09_kalendar_program_{safe}", f"{API}/api/calendar/program/{p['id']}.ics?token={tk}")

        # ── 7. Program archive reports (JSON) — for each program ──
        for i, p in enumerate(programs):
            safe = "".join(c if c.isalnum() else "_" for c in p["name_cs"][:30])
            await save(client, f"10_archive_report_{safe}", f"{API}/api/programs/{p['id']}/archive-report", H)

        # Create single ZIP bundle
        zip_path = f"{OUT}/VSECHNY_EXPORTY.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for m in manifest:
                if m.get("file") and os.path.exists(m["file"]):
                    z.write(m["file"], os.path.basename(m["file"]))

        # Manifest json
        with open(f"{OUT}/MANIFEST.json", "w", encoding="utf-8") as f:
            json.dump({"generated_at": datetime.now().isoformat(),
                       "files": manifest}, f, ensure_ascii=False, indent=2)

        print(f"Saved to: {OUT}")
        print(f"ZIP: {zip_path}")
        for m in manifest:
            size = f"{m.get('bytes', 0):>8} B" if "bytes" in m else "ERROR"
            print(f"  {size}  {os.path.basename(m.get('file','?'))}")
        print(f"\nTotal: {len(manifest)} files, {sum(m.get('bytes',0) for m in manifest)} bytes")


if __name__ == "__main__":
    asyncio.run(main())
