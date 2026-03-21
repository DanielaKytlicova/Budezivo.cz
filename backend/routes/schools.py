"""
Schools CRM routes - including PRO features.
Uses Supabase (PostgreSQL) for database operations.
"""
import io
import csv
import re
import logging
import uuid
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from models.schemas import School, PropagationRequest
from core.security import get_current_user
from database.supabase import get_db
from database.supabase_repositories import (
    SchoolRepositorySupabase,
    InstitutionRepositorySupabase,
    ProgramRepositorySupabase
)

router = APIRouter(prefix="/schools", tags=["Schools"])
logger = logging.getLogger(__name__)

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Required columns
REQUIRED_COLUMNS = ['název školy', 'email']
OPTIONAL_COLUMNS = ['telefon', 'město', 'poznámka', 'kontaktní osoba', 'ičo']

# Column mapping (various possible names)
COLUMN_MAPPING = {
    'název školy': ['název školy', 'nazev skoly', 'název', 'nazev', 'škola', 'skola', 'school', 'name'],
    'email': ['email', 'e-mail', 'mail', 'e mail'],
    'telefon': ['telefon', 'phone', 'tel', 'tel.', 'telephone'],
    'město': ['město', 'mesto', 'city', 'obec'],
    'poznámka': ['poznámka', 'poznamka', 'note', 'notes', 'poznámky'],
    'kontaktní osoba': ['kontaktní osoba', 'kontaktni osoba', 'kontakt', 'contact', 'contact person'],
    'ičo': ['ičo', 'ico', 'ic', 'ič'],
}


class ImportResult(BaseModel):
    success: bool
    total_rows: int
    imported: int
    skipped: int
    errors: int
    duplicates: int
    error_details: List[dict]


def normalize_column_name(name: str) -> Optional[str]:
    """Normalize column name to standard format."""
    name_lower = name.lower().strip()
    for standard_name, variations in COLUMN_MAPPING.items():
        if name_lower in variations:
            return standard_name
    return None


def validate_email(email: str) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def parse_excel_file(file_content: bytes, filename: str) -> tuple[List[dict], List[dict]]:
    """Parse Excel file and return rows with errors."""
    import openpyxl
    
    rows = []
    errors = []
    
    try:
        # Load workbook from bytes
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
        ws = wb.active
        
        # Get headers from first row
        headers = []
        for cell in ws[1]:
            if cell.value:
                normalized = normalize_column_name(str(cell.value))
                headers.append(normalized if normalized else str(cell.value).lower())
            else:
                headers.append(None)
        
        # Check required columns
        if 'název školy' not in headers:
            errors.append({"row": 0, "error": "Chybí povinný sloupec 'Název školy'"})
            return rows, errors
        if 'email' not in headers:
            errors.append({"row": 0, "error": "Chybí povinný sloupec 'Email'"})
            return rows, errors
        
        # Parse data rows
        for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            # Skip empty rows
            if not any(row):
                continue
            
            row_data = {}
            for col_idx, value in enumerate(row):
                if col_idx < len(headers) and headers[col_idx]:
                    row_data[headers[col_idx]] = str(value).strip() if value else ''
            
            # Validate required fields
            name = row_data.get('název školy', '').strip()
            email = row_data.get('email', '').strip()
            
            if not name:
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Chybí název školy"})
                continue
            
            if not email:
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Chybí email"})
                continue
            
            if not validate_email(email):
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Neplatný formát emailu '{email}'"})
                continue
            
            rows.append({
                'name': name,
                'email': email.lower(),
                'phone': row_data.get('telefon', ''),
                'city': row_data.get('město', ''),
                'notes': row_data.get('poznámka', ''),
                'contact_person': row_data.get('kontaktní osoba', ''),
                'ico': row_data.get('ičo', ''),
            })
        
        wb.close()
        
    except Exception as e:
        logger.error(f"Error parsing Excel file: {e}")
        errors.append({"row": 0, "error": f"Chyba při čtení souboru: {str(e)}"})
    
    return rows, errors


def parse_csv_file(file_content: bytes, filename: str) -> tuple[List[dict], List[dict]]:
    """Parse CSV file and return rows with errors."""
    rows = []
    errors = []
    
    try:
        # Detect encoding and delimiter
        content = file_content.decode('utf-8-sig')  # Handle BOM
        
        # Try different delimiters
        delimiter = ';' if ';' in content.split('\n')[0] else ','
        
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        
        # Normalize headers
        fieldnames = {}
        for field in reader.fieldnames or []:
            normalized = normalize_column_name(field)
            if normalized:
                fieldnames[field] = normalized
            else:
                fieldnames[field] = field.lower()
        
        # Check required columns
        normalized_fields = list(fieldnames.values())
        if 'název školy' not in normalized_fields:
            errors.append({"row": 0, "error": "Chybí povinný sloupec 'Název školy'"})
            return rows, errors
        if 'email' not in normalized_fields:
            errors.append({"row": 0, "error": "Chybí povinný sloupec 'Email'"})
            return rows, errors
        
        for row_idx, row in enumerate(reader, start=2):
            # Normalize row keys
            normalized_row = {}
            for key, value in row.items():
                norm_key = fieldnames.get(key, key.lower())
                normalized_row[norm_key] = value.strip() if value else ''
            
            # Validate required fields
            name = normalized_row.get('název školy', '').strip()
            email = normalized_row.get('email', '').strip()
            
            if not name and not email:
                continue  # Skip empty rows
            
            if not name:
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Chybí název školy"})
                continue
            
            if not email:
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Chybí email"})
                continue
            
            if not validate_email(email):
                errors.append({"row": row_idx, "error": f"Řádek {row_idx}: Neplatný formát emailu '{email}'"})
                continue
            
            rows.append({
                'name': name,
                'email': email.lower(),
                'phone': normalized_row.get('telefon', ''),
                'city': normalized_row.get('město', ''),
                'notes': normalized_row.get('poznámka', ''),
                'contact_person': normalized_row.get('kontaktní osoba', ''),
                'ico': normalized_row.get('ičo', ''),
            })
    
    except UnicodeDecodeError:
        # Try latin-1 encoding
        try:
            content = file_content.decode('latin-1')
            return parse_csv_file(content.encode('utf-8'), filename)
        except Exception as e:
            errors.append({"row": 0, "error": f"Chyba kódování souboru: {str(e)}"})
    except Exception as e:
        logger.error(f"Error parsing CSV file: {e}")
        errors.append({"row": 0, "error": f"Chyba při čtení souboru: {str(e)}"})
    
    return rows, errors


@router.get("", response_model=List[School])
async def get_schools(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all schools for institution."""
    school_repo = SchoolRepositorySupabase(db)
    return await school_repo.find_by_institution(current_user["institution_id"])


@router.get("/import-template")
async def download_import_template():
    """Download sample Excel template for school import."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Školy"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2B3E50", end_color="2B3E50", fill_type="solid")
    required_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Headers
    headers = ["Název školy", "Email", "Telefon", "Město", "Kontaktní osoba", "IČO", "Poznámka"]
    required_cols = [0, 1]  # First two columns are required
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = thin_border
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 20
    
    # Sample data
    sample_data = [
        ["ZŠ Příkladná", "info@zsprikladna.cz", "+420 123 456 789", "Praha", "Jan Novák", "12345678", "Aktivní kontakt"],
        ["MŠ Sluníčko", "skolka@slunicko.cz", "721 000 111", "Brno", "Marie Svobodová", "", ""],
        ["Gymnázium ABC", "sekretariat@gymnabc.cz", "", "Ostrava", "", "87654321", "Zájem o přírodovědné programy"],
    ]
    
    for row_idx, row_data in enumerate(sample_data, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if col_idx - 1 in required_cols:
                cell.fill = required_fill
    
    # Add instructions sheet
    ws_info = wb.create_sheet("Nápověda")
    instructions = [
        ["INSTRUKCE PRO IMPORT ŠKOL"],
        [""],
        ["Povinné sloupce (žluté):"],
        ["  - Název školy: Celý název školy"],
        ["  - Email: Platná emailová adresa (např. info@skola.cz)"],
        [""],
        ["Volitelné sloupce:"],
        ["  - Telefon: Telefonní číslo v libovolném formátu"],
        ["  - Město: Město/obec"],
        ["  - Kontaktní osoba: Jméno kontaktní osoby"],
        ["  - IČO: Identifikační číslo organizace"],
        ["  - Poznámka: Libovolná poznámka"],
        [""],
        ["Důležité:"],
        ["  - První řádek musí obsahovat názvy sloupců"],
        ["  - Duplicitní emaily budou přeskočeny"],
        ["  - Maximální velikost souboru: 10 MB"],
        ["  - Podporované formáty: .xlsx, .xls, .csv"],
    ]
    
    for row_idx, row in enumerate(instructions, 1):
        cell = ws_info.cell(row=row_idx, column=1, value=row[0] if row else "")
        if row_idx == 1:
            cell.font = Font(bold=True, size=14)
        ws_info.column_dimensions['A'].width = 60
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=vzorovy_import_skol.xlsx"}
    )


@router.post("/import", response_model=ImportResult)
async def import_schools(
    file: UploadFile = File(...),
    update_existing: bool = False,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import schools from Excel or CSV file.
    
    - Validates required columns (Název školy, Email)
    - Checks for duplicates by email
    - Returns detailed import results
    """
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Soubor je příliš velký (max 10 MB)")
    
    # Check file type
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in ['.xlsx', '.xls', '.csv']):
        raise HTTPException(status_code=400, detail="Nepodporovaný formát souboru. Použijte .xlsx, .xls nebo .csv")
    
    # Parse file
    if filename.endswith('.csv'):
        rows, errors = parse_csv_file(content, filename)
    else:
        rows, errors = parse_excel_file(content, filename)
    
    if not rows and errors:
        return ImportResult(
            success=False,
            total_rows=0,
            imported=0,
            skipped=0,
            errors=len(errors),
            duplicates=0,
            error_details=errors[:100]  # Limit errors
        )
    
    # Get existing schools
    school_repo = SchoolRepositorySupabase(db)
    existing_schools = await school_repo.find_by_institution(current_user["institution_id"])
    existing_emails = {s.get('email', '').lower() for s in existing_schools}
    existing_by_email = {s.get('email', '').lower(): s for s in existing_schools}
    
    imported = 0
    skipped = 0
    duplicates = 0
    
    # Track emails in this import to avoid duplicates within the file
    import_emails = set()
    
    for row in rows:
        email = row['email'].lower()
        
        # Check for duplicate within import file
        if email in import_emails:
            errors.append({"row": 0, "error": f"Duplicitní email v souboru: {email}"})
            duplicates += 1
            continue
        
        import_emails.add(email)
        
        # Check if already exists in database
        if email in existing_emails:
            if update_existing:
                # Update existing school
                existing = existing_by_email.get(email)
                if existing:
                    try:
                        await db.execute(text("""
                            UPDATE schools SET
                                name = :name,
                                phone = :phone,
                                city = :city,
                                contact_person = :contact,
                                ico = :ico,
                                notes = :notes,
                                updated_at = :updated
                            WHERE id = :id
                        """), {
                            "name": row['name'],
                            "phone": row.get('phone', ''),
                            "city": row.get('city', ''),
                            "contact": row.get('contact_person', ''),
                            "ico": row.get('ico', ''),
                            "notes": row.get('notes', ''),
                            "updated": datetime.now(timezone.utc),
                            "id": existing['id']
                        })
                        imported += 1
                    except Exception as e:
                        errors.append({"row": 0, "error": f"Chyba při aktualizaci {email}: {str(e)}"})
            else:
                duplicates += 1
            continue
        
        # Insert new school
        try:
            await db.execute(text("""
                INSERT INTO schools (id, institution_id, name, email, phone, city, contact_person, ico, notes, booking_count, created_at, updated_at)
                VALUES (:id, :institution_id, :name, :email, :phone, :city, :contact, :ico, :notes, :booking_count, :created, :updated)
            """), {
                "id": str(uuid.uuid4()),
                "institution_id": current_user["institution_id"],
                "name": row['name'],
                "email": email,
                "phone": row.get('phone', ''),
                "city": row.get('city', ''),
                "contact": row.get('contact_person', ''),
                "ico": row.get('ico', ''),
                "notes": row.get('notes', ''),
                "booking_count": 0,
                "created": datetime.now(timezone.utc),
                "updated": datetime.now(timezone.utc),
            })
            imported += 1
        except Exception as e:
            logger.error(f"Error inserting school: {e}")
            errors.append({"row": 0, "error": f"Chyba při ukládání {row['name']}: {str(e)}"})
    
    await db.commit()
    
    logger.info(f"School import completed: {imported} imported, {duplicates} duplicates, {len(errors)} errors")
    
    return ImportResult(
        success=imported > 0 or (len(rows) == 0 and len(errors) == 0),
        total_rows=len(rows),
        imported=imported,
        skipped=skipped,
        errors=len(errors),
        duplicates=duplicates,
        error_details=errors[:100]  # Limit to 100 errors
    )


@router.get("/import-errors")
async def download_import_errors(
    errors: str,
    current_user: dict = Depends(get_current_user)
):
    """Download import errors as CSV."""
    import json
    
    try:
        error_list = json.loads(errors)
    except:
        error_list = []
    
    output = io.StringIO()
    output.write("Řádek;Chyba\n")
    for err in error_list:
        output.write(f"{err.get('row', '')};{err.get('error', '')}\n")
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=import_chyby.csv"}
    )


@router.get("/export-csv")
async def export_schools_csv(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export schools to CSV - PRO feature only."""
    institution_repo = InstitutionRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    
    # Check PRO status
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution or institution.get("plan") not in ["standard", "premium"]:
        raise HTTPException(status_code=403, detail="Tato funkce je dostupná pouze v PRO verzi")
    
    # Get schools
    schools = await school_repo.find_by_institution(current_user["institution_id"])
    
    # Generate CSV
    output = io.StringIO()
    output.write("Název školy;IČO;Email;Telefon;Město;Datum registrace\n")
    for school in schools:
        created = school.get("created_at", "")
        if hasattr(created, "strftime"):
            created = created.strftime("%d.%m.%Y")
        output.write(f"{school.get('name', '')};{school.get('ico', '')};{school.get('email', '')};{school.get('phone', '')};{school.get('city', '')};{created}\n")
    
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=skoly_export.csv"}
    )


@router.post("/send-propagation")
async def send_propagation(
    request: PropagationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send program promotion to schools - PRO feature only."""
    institution_repo = InstitutionRepositorySupabase(db)
    program_repo = ProgramRepositorySupabase(db)
    school_repo = SchoolRepositorySupabase(db)
    
    # Check PRO status
    institution = await institution_repo.find_by_id(current_user["institution_id"])
    if not institution or institution.get("plan") not in ["standard", "premium"]:
        raise HTTPException(status_code=403, detail="Tato funkce je dostupná pouze v PRO verzi")
    
    # Get program
    program = await program_repo.find_by_id(request.program_id, current_user["institution_id"])
    if not program:
        raise HTTPException(status_code=404, detail="Program nenalezen")
    
    # Get schools
    schools = await school_repo.find_by_ids(current_user["institution_id"], request.school_ids)
    if not schools:
        raise HTTPException(status_code=400, detail="Nebyly vybrány žádné školy")
    
    # Get PRO settings
    pro_settings = institution.get("pro_settings", {}) or {}
    subject = pro_settings.get("email_subject_template", "Nový program: {program_name}")
    body = pro_settings.get("email_body_template", 
        "Dobrý den,\n\nrádi bychom Vás informovali o novém programu {program_name}.\n\n"
        "{program_description}\n\nRezervovat můžete zde: {reservation_url}\n\n"
        "S pozdravem,\n{institution_name}"
    )
    
    reservation_url = f"https://www.budezivo.cz/booking/{current_user['institution_id']}?program={request.program_id}"
    
    # Format email
    subject = subject.replace("{program_name}", program.get("name_cs", ""))
    body = body.replace("{program_name}", program.get("name_cs", ""))
    body = body.replace("{program_description}", program.get("description_cs", ""))
    body = body.replace("{reservation_url}", reservation_url)
    body = body.replace("{institution_name}", institution.get("name", ""))
    
    # Mock send emails
    sent_count = 0
    for school in schools:
        logger.info(f"[PROPAGATION] Sending to {school.get('email')}: {subject}")
        sent_count += 1
    
    return {
        "message": f"Propagace odeslána {sent_count} školám",
        "sent_count": sent_count,
        "schools": [s.get("name") for s in schools]
    }
