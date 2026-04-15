"""
Export service for event applications.
Generates XLSX, CSV, and PDF exports.
"""
import io
import csv
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    'pending': 'Čeká na schválení',
    'approved': 'Schváleno',
    'rejected': 'Zamítnuto',
}

PAYMENT_LABELS = {
    'unpaid': 'Nezaplaceno',
    'pending': 'Čeká na platbu',
    'paid': 'Zaplaceno',
}


def _build_field_label_map(form_fields: list) -> dict:
    """Map field IDs to labels."""
    return {f.get('id', ''): f.get('label', f.get('id', '')) for f in (form_fields or [])}


def _format_date(iso: str) -> str:
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except Exception:
        return iso[:10] if len(iso) >= 10 else iso


def _get_app_rows(applications: list, field_map: dict) -> tuple:
    """Build header + data rows from applications."""
    # Fixed columns
    fixed_headers = ['Jméno', 'Email', 'Status', 'Platba', 'Částka', 'VS', 'Datum přihlášení']
    
    # Dynamic field columns (from form_fields)
    dynamic_keys = list(field_map.keys())
    dynamic_headers = [field_map[k] for k in dynamic_keys]
    
    headers = fixed_headers + dynamic_headers
    rows = []
    
    for app in applications:
        data = app.get('applicant_data', {}) or {}
        row = [
            app.get('applicant_name', ''),
            app.get('applicant_email', ''),
            STATUS_LABELS.get(app.get('status', ''), app.get('status', '')),
            PAYMENT_LABELS.get(app.get('payment_status', ''), app.get('payment_status', '')),
            f"{app.get('total_amount', 0)} Kč",
            app.get('variable_symbol', ''),
            _format_date(app.get('created_at', '')),
        ]
        for key in dynamic_keys:
            val = data.get(key, '')
            if isinstance(val, bool):
                val = 'Ano' if val else 'Ne'
            row.append(str(val))
        rows.append(row)
    
    return headers, rows


# ============ XLSX Export ============

def generate_xlsx(event: dict, applications: list) -> io.BytesIO:
    """Generate styled XLSX export of applications."""
    form_fields = event.get('form_fields', [])
    field_map = _build_field_label_map(form_fields)
    headers, rows = _get_app_rows(applications, field_map)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Přihlášky"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0'),
    )
    
    paid_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    unpaid_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    pending_fill = PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid")
    
    # Title row
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 1))
    title_cell = ws.cell(row=1, column=1, value=f"Přihlášky — {event.get('name', 'Událost')}")
    title_cell.font = Font(bold=True, size=14, color="1E293B")
    title_cell.alignment = Alignment(horizontal="left")
    
    # Subtitle
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=max(len(headers), 1))
    sub_cell = ws.cell(row=2, column=1, value=f"Exportováno: {datetime.now().strftime('%d.%m.%Y %H:%M')} | Celkem: {len(applications)} přihlášek")
    sub_cell.font = Font(size=10, color="64748B")
    
    # Headers (row 4)
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border
    
    # Data rows
    for row_idx, row_data in enumerate(rows, 5):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            
            # Conditional formatting for payment status column (index 3, col 4)
            if col_idx == 4:
                if value == PAYMENT_LABELS['paid']:
                    cell.fill = paid_fill
                    cell.font = Font(color="166534", bold=True)
                elif value == PAYMENT_LABELS['unpaid']:
                    cell.fill = unpaid_fill
                    cell.font = Font(color="991B1B")
                elif value == PAYMENT_LABELS['pending']:
                    cell.fill = pending_fill
                    cell.font = Font(color="92400E")
        
        # Alternate row shading
        if row_idx % 2 == 0:
            for col_idx in range(1, len(row_data) + 1):
                if ws.cell(row=row_idx, column=col_idx).fill == PatternFill():
                    ws.cell(row=row_idx, column=col_idx).fill = PatternFill(
                        start_color="F8FAFC", end_color="F8FAFC", fill_type="solid"
                    )
    
    # Auto-width columns
    for col_idx, header in enumerate(headers, 1):
        max_len = len(header)
        for row_idx in range(5, 5 + len(rows)):
            cell_val = str(ws.cell(row=row_idx, column=col_idx).value or '')
            max_len = max(max_len, len(cell_val))
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = min(max_len + 4, 40)
    
    # Summary row
    summary_row = 5 + len(rows) + 1
    ws.cell(row=summary_row, column=1, value="Celkem").font = Font(bold=True)
    
    paid_count = sum(1 for a in applications if a.get('payment_status') == 'paid')
    total_amount = sum(a.get('total_amount', 0) for a in applications)
    ws.cell(row=summary_row, column=4, value=f"Zaplaceno: {paid_count}/{len(applications)}").font = Font(bold=True)
    ws.cell(row=summary_row, column=5, value=f"{total_amount} Kč").font = Font(bold=True)
    
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


# ============ CSV Export ============

def generate_csv(event: dict, applications: list) -> io.BytesIO:
    """Generate CSV export with UTF-8 BOM for Excel compatibility."""
    form_fields = event.get('form_fields', [])
    field_map = _build_field_label_map(form_fields)
    headers, rows = _get_app_rows(applications, field_map)
    
    buffer = io.BytesIO()
    # UTF-8 BOM for Excel
    buffer.write(b'\xef\xbb\xbf')
    
    # Write CSV content as bytes directly
    lines = []
    def csv_escape(val):
        s = str(val).replace('"', '""')
        if ';' in s or '"' in s or '\n' in s:
            return f'"{s}"'
        return s
    
    lines.append(';'.join(csv_escape(h) for h in headers))
    for row in rows:
        lines.append(';'.join(csv_escape(v) for v in row))
    
    buffer.write('\n'.join(lines).encode('utf-8'))
    buffer.seek(0)
    return buffer


# ============ PDF Confirmation ============

def generate_pdf_confirmation(
    application: dict,
    event: dict,
    event_date: Optional[dict],
    institution: dict,
    payment_settings: Optional[dict],
) -> io.BytesIO:
    """Generate PDF confirmation for a single application with QR payment."""
    buffer = io.BytesIO()
    
    # Register DejaVuSans for Czech diacritics
    import os
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font_bold_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVuSans', font_path))
    if os.path.exists(font_bold_path):
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_bold_path))
    
    base_font = 'DejaVuSans' if os.path.exists(font_path) else 'Helvetica'
    bold_font = 'DejaVuSans-Bold' if os.path.exists(font_bold_path) else 'Helvetica-Bold'
    
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='InstitutionName',
        fontSize=18, leading=22, spaceAfter=4,
        textColor=colors.HexColor('#1E293B'),
        fontName=bold_font,
    ))
    styles.add(ParagraphStyle(
        name='DocTitle',
        fontSize=14, leading=18, spaceAfter=12, spaceBefore=8,
        textColor=colors.HexColor('#334155'),
        fontName=bold_font,
    ))
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontSize=11, leading=14, spaceAfter=6, spaceBefore=12,
        textColor=colors.HexColor('#1E293B'),
        fontName=bold_font,
    ))
    styles.add(ParagraphStyle(
        name='BodyText2',
        fontSize=10, leading=14, spaceAfter=4,
        textColor=colors.HexColor('#475569'),
        fontName=base_font,
    ))
    styles.add(ParagraphStyle(
        name='Footer',
        fontSize=8, leading=10,
        textColor=colors.HexColor('#94A3B8'),
        alignment=1,
        fontName=base_font,
    ))
    
    elements = []
    
    # ── Header ──
    inst_name = institution.get('name', 'Instituce')
    elements.append(Paragraph(inst_name, styles['InstitutionName']))
    elements.append(Spacer(1, 2*mm))
    
    # Divider line
    elements.append(Table(
        [['']],
        colWidths=[170*mm],
        style=TableStyle([
            ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#E2E8F0')),
        ])
    ))
    elements.append(Spacer(1, 4*mm))
    
    # ── Title ──
    elements.append(Paragraph("Potvrzení přihlášky", styles['DocTitle']))
    
    # ── Event info ──
    elements.append(Paragraph("Událost", styles['SectionTitle']))
    
    event_data = [
        ['Název:', event.get('name', '')],
        ['Typ:', {'event': 'Akce', 'camp': 'Příměstský tábor', 'workshop': 'Workshop', 'course': 'Kurz'}.get(event.get('type', ''), event.get('type', ''))],
    ]
    if event_date:
        event_data.append(['Termín:', f"{_format_date(event_date.get('start_datetime', ''))} — {_format_date(event_date.get('end_datetime', ''))}"])
    if event.get('price', 0) > 0:
        event_data.append(['Cena:', f"{event.get('price', 0)} {event.get('currency', 'Kč')}"])
    
    event_table = Table(event_data, colWidths=[35*mm, 135*mm])
    event_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), base_font),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748B')),
        ('FONTNAME', (1, 0), (1, -1), bold_font),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1E293B')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(event_table)
    
    # ── Applicant info ──
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("Údaje účastníka", styles['SectionTitle']))
    
    applicant_rows = []
    if application.get('applicant_name'):
        applicant_rows.append(['Jméno:', application['applicant_name']])
    if application.get('applicant_email'):
        applicant_rows.append(['Email:', application['applicant_email']])
    
    # Dynamic form fields
    field_map = _build_field_label_map(event.get('form_fields', []))
    app_data = application.get('applicant_data', {}) or {}
    for key, val in app_data.items():
        label = field_map.get(key, key)
        if isinstance(val, bool):
            val = 'Ano' if val else 'Ne'
        applicant_rows.append([f"{label}:", str(val)])
    
    if applicant_rows:
        app_table = Table(applicant_rows, colWidths=[45*mm, 125*mm])
        app_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), base_font),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748B')),
            ('FONTNAME', (1, 0), (1, -1), base_font),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1E293B')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(app_table)
    
    # ── Payment section ──
    total = application.get('total_amount', 0)
    vs = application.get('variable_symbol', '')
    
    if total and total > 0 and payment_settings:
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph("Platební údaje", styles['SectionTitle']))
        
        acc_num = payment_settings.get('account_number', '')
        bank_code = payment_settings.get('bank_code', '')
        acc_name = payment_settings.get('account_name', '')
        
        pay_rows = []
        if acc_num:
            pay_rows.append(['Číslo účtu:', f"{acc_num}/{bank_code}" if bank_code else acc_num])
        if acc_name:
            pay_rows.append(['Příjemce:', acc_name])
        pay_rows.append(['Částka:', f"{total} Kč"])
        pay_rows.append(['Variabilní symbol:', vs])
        
        pay_table = Table(pay_rows, colWidths=[45*mm, 125*mm])
        pay_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), base_font),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#64748B')),
            ('FONTNAME', (1, 0), (1, -1), bold_font),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#1E293B')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ]))
        elements.append(pay_table)
        
        # QR code
        if acc_num and vs:
            try:
                import qrcode
                from reportlab.lib.utils import ImageReader
                
                acc = f"{acc_num}/{bank_code}" if bank_code else acc_num
                spayd = f"SPD*1.0*ACC:CZ{acc}*AM:{total:.2f}*CC:CZK*X-VS:{vs}*MSG:Prihlaska"
                
                qr = qrcode.QRCode(version=1, box_size=6, border=2)
                qr.add_data(spayd)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                qr_buffer = io.BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                
                elements.append(Spacer(1, 4*mm))
                elements.append(Paragraph("QR platba:", styles['BodyText2']))
                qr_rl = RLImage(qr_buffer, width=40*mm, height=40*mm)
                elements.append(qr_rl)
                elements.append(Paragraph("Naskenujte QR kód v bankovní aplikaci.", styles['BodyText2']))
            except Exception as e:
                logger.warning(f"QR generation failed: {e}")
    
    # ── Status ──
    elements.append(Spacer(1, 6*mm))
    status_text = STATUS_LABELS.get(application.get('status', ''), application.get('status', ''))
    payment_text = PAYMENT_LABELS.get(application.get('payment_status', ''), application.get('payment_status', ''))
    elements.append(Paragraph(f"Status přihlášky: <b>{status_text}</b>  |  Platba: <b>{payment_text}</b>", styles['BodyText2']))
    
    # ── Footer ──
    elements.append(Spacer(1, 10*mm))
    elements.append(Table(
        [['']],
        colWidths=[170*mm],
        style=TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0'))])
    ))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f"Vygenerováno systémem Budeživo.cz | {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        styles['Footer']
    ))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer
