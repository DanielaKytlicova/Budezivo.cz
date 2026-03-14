"""
Email Templates for Budeživo.cz
React Email compatible HTML templates for transactional emails.
"""
from typing import Dict, Any

# Base styles used across all templates
BASE_STYLES = {
    "container": "font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;",
    "header": "background-color: #1E293B; padding: 24px; text-align: center;",
    "logo": "color: #ffffff; font-size: 24px; font-weight: bold; margin: 0;",
    "content": "padding: 32px 24px;",
    "h1": "color: #1E293B; font-size: 24px; font-weight: 600; margin: 0 0 16px 0;",
    "h2": "color: #334155; font-size: 18px; font-weight: 600; margin: 24px 0 12px 0;",
    "text": "color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;",
    "info_box": "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin: 20px 0;",
    "info_row": "display: flex; padding: 8px 0; border-bottom: 1px solid #E2E8F0;",
    "info_label": "color: #64748B; font-size: 14px; width: 140px;",
    "info_value": "color: #1E293B; font-size: 14px; font-weight: 500;",
    "button": "display: inline-block; background-color: #1E293B; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 15px;",
    "button_secondary": "display: inline-block; background-color: #84A98C; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 15px;",
    "button_danger": "display: inline-block; background-color: #DC2626; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 500; font-size: 15px;",
    "footer": "background-color: #F8FAFC; padding: 24px; text-align: center; border-top: 1px solid #E2E8F0;",
    "footer_text": "color: #64748B; font-size: 12px; line-height: 1.5; margin: 0;",
    "divider": "border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;",
    "alert_success": "background-color: #ECFDF5; border: 1px solid #10B981; border-radius: 6px; padding: 16px; color: #065F46;",
    "alert_warning": "background-color: #FFFBEB; border: 1px solid #F59E0B; border-radius: 6px; padding: 16px; color: #92400E;",
    "alert_error": "background-color: #FEF2F2; border: 1px solid #EF4444; border-radius: 6px; padding: 16px; color: #991B1B;",
}


def _base_template(content: str, footer_extra: str = "") -> str:
    """Wrap content in base email template."""
    return f"""
<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Budeživo.cz</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F1F5F9;">
    <table role="presentation" style="width: 100%; border-collapse: collapse;">
        <tr>
            <td style="padding: 40px 20px;">
                <div style="{BASE_STYLES['container']}">
                    <!-- Header -->
                    <div style="{BASE_STYLES['header']}">
                        <h1 style="{BASE_STYLES['logo']}">Budeživo.cz</h1>
                    </div>
                    
                    <!-- Content -->
                    <div style="{BASE_STYLES['content']}">
                        {content}
                    </div>
                    
                    <!-- Footer -->
                    <div style="{BASE_STYLES['footer']}">
                        <p style="{BASE_STYLES['footer_text']}">
                            Tento email byl odeslán automaticky systémem Budeživo.cz<br>
                            Pokud máte dotazy, kontaktujte nás na info@budezivo.cz
                            {footer_extra}
                        </p>
                    </div>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def _plain_text_base(content: str) -> str:
    """Create plain text version of email."""
    return f"""
Budeživo.cz
{'=' * 40}

{content}

{'=' * 40}
Tento email byl odeslán automaticky systémem Budeživo.cz
Pokud máte dotazy, kontaktujte nás na info@budezivo.cz
"""


# ============ ACCOUNT TEMPLATES ============

def user_registration_confirmation(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent after user registration."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Vítejte v Budeživo.cz!</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('user_name', '')},
        </p>
        
        <p style="{BASE_STYLES['text']}">
            děkujeme za registraci instituce <strong>{data.get('institution_name', '')}</strong> 
            v rezervačním systému Budeživo.cz.
        </p>
        
        <p style="{BASE_STYLES['text']}">
            Váš účet byl úspěšně vytvořen a můžete se nyní přihlásit a začít spravovat 
            své vzdělávací programy.
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('dashboard_url', 'https://budezivo.cz/admin')}" style="{BASE_STYLES['button']}">
                Přejít do administrace
            </a>
        </div>
        
        <div style="{BASE_STYLES['info_box']}">
            <h2 style="{BASE_STYLES['h2']}; margin-top: 0;">Co můžete dělat dál?</h2>
            <ul style="color: #475569; padding-left: 20px; margin: 0;">
                <li style="margin-bottom: 8px;">Vytvořit své první vzdělávací programy</li>
                <li style="margin-bottom: 8px;">Nastavit dostupné termíny</li>
                <li style="margin-bottom: 8px;">Sdílet odkaz na rezervační stránku se školami</li>
            </ul>
        </div>
    """
    
    plain = f"""
Vítejte v Budeživo.cz!

Dobrý den, {data.get('user_name', '')},

děkujeme za registraci instituce {data.get('institution_name', '')} v rezervačním systému Budeživo.cz.

Váš účet byl úspěšně vytvořen. Přihlaste se zde: {data.get('dashboard_url', 'https://budezivo.cz/admin')}

Co můžete dělat dál?
- Vytvořit své první vzdělávací programy
- Nastavit dostupné termíny  
- Sdílet odkaz na rezervační stránku se školami
"""
    
    return {
        "subject": "Vítejte v Budeživo.cz!",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def account_activation(data: Dict[str, Any]) -> Dict[str, str]:
    """Account activation email."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Aktivujte svůj účet</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('user_name', '')},
        </p>
        
        <p style="{BASE_STYLES['text']}">
            pro aktivaci vašeho účtu v systému Budeživo.cz klikněte na tlačítko níže.
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('activation_link', '#')}" style="{BASE_STYLES['button']}">
                Aktivovat účet
            </a>
        </div>
        
        <p style="{BASE_STYLES['text']}; font-size: 13px; color: #64748B;">
            Pokud tlačítko nefunguje, zkopírujte tento odkaz do prohlížeče:<br>
            <a href="{data.get('activation_link', '#')}" style="color: #1E293B; word-break: break-all;">
                {data.get('activation_link', '#')}
            </a>
        </p>
        
        <hr style="{BASE_STYLES['divider']}">
        
        <p style="{BASE_STYLES['text']}; font-size: 13px; color: #64748B;">
            Pokud jste si účet nezakládali, tento email ignorujte.
        </p>
    """
    
    plain = f"""
Aktivujte svůj účet

Dobrý den, {data.get('user_name', '')},

pro aktivaci vašeho účtu v systému Budeživo.cz přejděte na tento odkaz:
{data.get('activation_link', '#')}

Pokud jste si účet nezakládali, tento email ignorujte.
"""
    
    return {
        "subject": "Aktivujte svůj účet - Budeživo.cz",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def password_reset(data: Dict[str, Any]) -> Dict[str, str]:
    """Password reset request email."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Obnovení hesla</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den,
        </p>
        
        <p style="{BASE_STYLES['text']}">
            obdrželi jsme žádost o obnovení hesla pro účet spojený s emailem 
            <strong>{data.get('user_email', '')}</strong>.
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('reset_link', '#')}" style="{BASE_STYLES['button']}">
                Obnovit heslo
            </a>
        </div>
        
        <p style="{BASE_STYLES['text']}; font-size: 13px; color: #64748B;">
            Odkaz je platný po dobu 1 hodiny. Pokud tlačítko nefunguje, zkopírujte tento odkaz:<br>
            <a href="{data.get('reset_link', '#')}" style="color: #1E293B; word-break: break-all;">
                {data.get('reset_link', '#')}
            </a>
        </p>
        
        <div style="{BASE_STYLES['alert_warning']}">
            <strong>Bezpečnostní upozornění:</strong><br>
            Pokud jste o obnovení hesla nežádali, tento email ignorujte. Vaše heslo zůstane nezměněné.
        </div>
    """
    
    plain = f"""
Obnovení hesla

Dobrý den,

obdrželi jsme žádost o obnovení hesla pro účet spojený s emailem {data.get('user_email', '')}.

Pro obnovení hesla přejděte na tento odkaz (platný 1 hodinu):
{data.get('reset_link', '#')}

Pokud jste o obnovení hesla nežádali, tento email ignorujte.
"""
    
    return {
        "subject": "Obnovení hesla - Budeživo.cz",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def password_changed(data: Dict[str, Any]) -> Dict[str, str]:
    """Password changed confirmation email."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Heslo bylo změněno</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('user_name', '')},
        </p>
        
        <div style="{BASE_STYLES['alert_success']}">
            <strong>✓ Heslo úspěšně změněno</strong><br>
            Vaše heslo k účtu {data.get('user_email', '')} bylo právě změněno.
        </div>
        
        <p style="{BASE_STYLES['text']}">
            Pokud jste tuto změnu neprovedli, okamžitě nás kontaktujte na 
            <a href="mailto:info@budezivo.cz" style="color: #1E293B;">info@budezivo.cz</a>.
        </p>
    """
    
    plain = f"""
Heslo bylo změněno

Dobrý den, {data.get('user_name', '')},

vaše heslo k účtu {data.get('user_email', '')} bylo právě změněno.

Pokud jste tuto změnu neprovedli, okamžitě nás kontaktujte na info@budezivo.cz.
"""
    
    return {
        "subject": "Heslo bylo změněno - Budeživo.cz",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


# ============ RESERVATION TEMPLATES ============

def _reservation_details_box(data: Dict[str, Any]) -> str:
    """Reusable reservation details box."""
    return f"""
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 140px;">Program:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500;">{data.get('program_name', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Datum:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('reservation_date', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Čas:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('reservation_time', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Škola:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('school_name', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Počet dětí:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('children_count', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Počet pedagogů:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('teachers_count', 0)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Kontakt:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">
                        {data.get('teacher_name', '')}<br>
                        <span style="font-weight: normal;">{data.get('teacher_email', '')}</span><br>
                        <span style="font-weight: normal;">{data.get('teacher_phone', '')}</span>
                    </td>
                </tr>
            </table>
        </div>
    """


def reservation_created_teacher(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher after creating reservation."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace byla přijata</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <p style="{BASE_STYLES['text']}">
            děkujeme za vytvoření rezervace v instituci <strong>{data.get('institution_name', '')}</strong>. 
            Vaše rezervace byla přijata a čeká na potvrzení.
        </p>
        
        {_reservation_details_box(data)}
        
        <div style="{BASE_STYLES['alert_warning']}">
            <strong>⏳ Čeká na potvrzení</strong><br>
            O potvrzení rezervace vás budeme informovat emailem.
        </div>
        
        <p style="{BASE_STYLES['text']}">
            V případě dotazů nás kontaktujte na {data.get('institution_email', '')} 
            nebo {data.get('institution_phone', '')}.
        </p>
    """
    
    plain = f"""
Rezervace byla přijata

Dobrý den, {data.get('teacher_name', '')},

děkujeme za vytvoření rezervace v instituci {data.get('institution_name', '')}.

Detail rezervace:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}
- Škola: {data.get('school_name', '')}
- Počet dětí: {data.get('children_count', 0)}

Vaše rezervace čeká na potvrzení. O dalším postupu vás budeme informovat.

Kontakt: {data.get('institution_email', '')} / {data.get('institution_phone', '')}
"""
    
    return {
        "subject": f"Rezervace přijata - {data.get('program_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_created_institution(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to institution after new reservation."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Nová rezervace k potvrzení</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den,
        </p>
        
        <p style="{BASE_STYLES['text']}">
            byla vytvořena nová rezervace, která čeká na vaše potvrzení.
        </p>
        
        {_reservation_details_box(data)}
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('dashboard_url', 'https://budezivo.cz/admin')}/bookings" style="{BASE_STYLES['button']}">
                Zobrazit rezervaci
            </a>
        </div>
    """
    
    plain = f"""
Nová rezervace k potvrzení

Byla vytvořena nová rezervace:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}
- Škola: {data.get('school_name', '')}
- Kontakt: {data.get('teacher_name', '')} ({data.get('teacher_email', '')})

Přejděte do administrace pro potvrzení: {data.get('dashboard_url', 'https://budezivo.cz/admin')}/bookings
"""
    
    return {
        "subject": f"Nová rezervace - {data.get('school_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_confirmed(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when reservation is confirmed."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace potvrzena!</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <div style="{BASE_STYLES['alert_success']}">
            <strong>✓ Rezervace potvrzena</strong><br>
            Vaše rezervace v instituci {data.get('institution_name', '')} byla potvrzena.
        </div>
        
        {_reservation_details_box(data)}
        
        <h2 style="{BASE_STYLES['h2']}">Důležité informace</h2>
        <ul style="color: #475569; padding-left: 20px;">
            <li style="margin-bottom: 8px;">Dostavte se prosím 10 minut před začátkem programu</li>
            <li style="margin-bottom: 8px;">V případě nemoci nebo neúčasti nás kontaktujte nejpozději 2 dny předem</li>
        </ul>
        
        <p style="{BASE_STYLES['text']}">
            Těšíme se na vaši návštěvu!
        </p>
        
        <p style="{BASE_STYLES['text']}">
            <strong>{data.get('institution_name', '')}</strong><br>
            {data.get('institution_address', '')}<br>
            {data.get('institution_email', '')} | {data.get('institution_phone', '')}
        </p>
    """
    
    plain = f"""
Rezervace potvrzena!

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace v instituci {data.get('institution_name', '')} byla potvrzena.

Detail:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}

Důležité informace:
- Dostavte se prosím 10 minut před začátkem
- V případě nemoci nás kontaktujte nejpozději 2 dny předem

Těšíme se na vaši návštěvu!

{data.get('institution_name', '')}
{data.get('institution_email', '')} | {data.get('institution_phone', '')}
"""
    
    return {
        "subject": f"✓ Rezervace potvrzena - {data.get('program_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_rejected(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when reservation is rejected."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace nebyla potvrzena</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <div style="{BASE_STYLES['alert_error']}">
            <strong>✗ Rezervace odmítnuta</strong><br>
            Vaše rezervace bohužel nemohla být potvrzena.
        </div>
        
        {_reservation_details_box(data)}
        
        <h2 style="{BASE_STYLES['h2']}">Důvod odmítnutí</h2>
        <p style="{BASE_STYLES['text']}">
            {data.get('rejection_reason', 'Důvod nebyl uveden.')}
        </p>
        
        <p style="{BASE_STYLES['text']}">
            Pro více informací nebo nalezení alternativního termínu nás prosím kontaktujte.
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('booking_url', '#')}" style="{BASE_STYLES['button_secondary']}">
                Vybrat jiný termín
            </a>
        </div>
    """
    
    plain = f"""
Rezervace nebyla potvrzena

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace bohužel nemohla být potvrzena.

Detail:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}

Důvod odmítnutí: {data.get('rejection_reason', 'Důvod nebyl uveden.')}

Pro nalezení alternativního termínu nás kontaktujte nebo navštivte: {data.get('booking_url', '#')}
"""
    
    return {
        "subject": f"Rezervace odmítnuta - {data.get('program_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_updated(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when reservation is updated."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace byla aktualizována</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <p style="{BASE_STYLES['text']}">
            vaše rezervace v instituci <strong>{data.get('institution_name', '')}</strong> byla aktualizována.
        </p>
        
        <h2 style="{BASE_STYLES['h2']}">Aktuální informace</h2>
        {_reservation_details_box(data)}
        
        <p style="{BASE_STYLES['text']}">
            V případě dotazů nás kontaktujte na {data.get('institution_email', '')}.
        </p>
    """
    
    plain = f"""
Rezervace byla aktualizována

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace v instituci {data.get('institution_name', '')} byla aktualizována.

Aktuální detail:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}

Kontakt: {data.get('institution_email', '')}
"""
    
    return {
        "subject": f"Rezervace aktualizována - {data.get('program_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_cancelled(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when reservation is cancelled."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace byla zrušena</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <div style="{BASE_STYLES['alert_error']}">
            <strong>✗ Rezervace zrušena</strong><br>
            Vaše rezervace v instituci {data.get('institution_name', '')} byla zrušena.
        </div>
        
        {_reservation_details_box(data)}
        
        <h2 style="{BASE_STYLES['h2']}">Důvod zrušení</h2>
        <p style="{BASE_STYLES['text']}">
            {data.get('cancellation_reason', 'Důvod nebyl uveden.')}
        </p>
        
        <p style="{BASE_STYLES['text']}">
            Pokud máte zájem o jiný termín, můžete vytvořit novou rezervaci.
        </p>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('booking_url', '#')}" style="{BASE_STYLES['button']}">
                Vytvořit novou rezervaci
            </a>
        </div>
    """
    
    plain = f"""
Rezervace byla zrušena

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace v instituci {data.get('institution_name', '')} byla zrušena.

Detail:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}

Důvod zrušení: {data.get('cancellation_reason', 'Důvod nebyl uveden.')}

Pro vytvoření nové rezervace navštivte: {data.get('booking_url', '#')}
"""
    
    return {
        "subject": f"Rezervace zrušena - {data.get('program_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


# ============ REMINDER TEMPLATES ============

def reservation_reminder_teacher(data: Dict[str, Any]) -> Dict[str, str]:
    """Reminder email sent to teacher before reservation."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Připomínka rezervace</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>
        
        <div style="{BASE_STYLES['alert_warning']}">
            <strong>📅 Blíží se váš program!</strong><br>
            Vaše rezervace se koná <strong>{data.get('reservation_date', '')}</strong> v <strong>{data.get('reservation_time', '')}</strong>.
        </div>
        
        {_reservation_details_box(data)}
        
        <h2 style="{BASE_STYLES['h2']}">Nezapomeňte</h2>
        <ul style="color: #475569; padding-left: 20px;">
            <li style="margin-bottom: 8px;">Dostavte se 10 minut před začátkem</li>
            <li style="margin-bottom: 8px;">Ujistěte se, že máte potvrzený počet účastníků</li>
        </ul>
        
        <p style="{BASE_STYLES['text']}">
            <strong>{data.get('institution_name', '')}</strong><br>
            {data.get('institution_address', '')}
        </p>
    """
    
    plain = f"""
Připomínka rezervace

Dobrý den, {data.get('teacher_name', '')},

připomínáme vaši nadcházející rezervaci:

- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}
- Místo: {data.get('institution_name', '')}, {data.get('institution_address', '')}

Dostavte se prosím 10 minut před začátkem.
"""
    
    return {
        "subject": f"Připomínka: {data.get('program_name', '')} - {data.get('reservation_date', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_reminder_institution(data: Dict[str, Any]) -> Dict[str, str]:
    """Reminder email sent to institution before reservation."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Nadcházející rezervace</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den,
        </p>
        
        <div style="{BASE_STYLES['alert_warning']}">
            <strong>📅 Zítra máte naplánovaný program</strong>
        </div>
        
        {_reservation_details_box(data)}
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('dashboard_url', 'https://budezivo.cz/admin')}/bookings" style="{BASE_STYLES['button']}">
                Zobrazit detail
            </a>
        </div>
    """
    
    plain = f"""
Nadcházející rezervace

Zítra máte naplánovaný program:

- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}
- Škola: {data.get('school_name', '')}
- Kontakt: {data.get('teacher_name', '')} ({data.get('teacher_email', '')})
"""
    
    return {
        "subject": f"Zítra: {data.get('program_name', '')} - {data.get('school_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


# ============ ADMIN TEMPLATES ============

def new_institution_registration(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to admin when new institution registers."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Nová registrace instituce</h1>
        
        <p style="{BASE_STYLES['text']}">
            Byla zaregistrována nová instituce v systému Budeživo.cz.
        </p>
        
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 140px;">Název:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500;">{data.get('institution_name', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Typ:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('institution_type', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Admin email:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('user_email', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Město:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('institution_city', '')}</td>
                </tr>
            </table>
        </div>
    """
    
    plain = f"""
Nová registrace instituce

Byla zaregistrována nová instituce:
- Název: {data.get('institution_name', '')}
- Typ: {data.get('institution_type', '')}
- Admin: {data.get('user_email', '')}
- Město: {data.get('institution_city', '')}
"""
    
    return {
        "subject": f"Nová registrace: {data.get('institution_name', '')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


# ============ TEMPLATE REGISTRY ============

TEMPLATE_REGISTRY = {
    "user_registration_confirmation": user_registration_confirmation,
    "account_activation": account_activation,
    "password_reset": password_reset,
    "password_changed": password_changed,
    "reservation_created_teacher": reservation_created_teacher,
    "reservation_created_institution": reservation_created_institution,
    "reservation_confirmed": reservation_confirmed,
    "reservation_rejected": reservation_rejected,
    "reservation_updated": reservation_updated,
    "reservation_cancelled": reservation_cancelled,
    "reservation_reminder_teacher": reservation_reminder_teacher,
    "reservation_reminder_institution": reservation_reminder_institution,
    "new_institution_registration": new_institution_registration,
}


def get_template(template_name: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Get rendered template by name."""
    template_func = TEMPLATE_REGISTRY.get(template_name)
    if not template_func:
        raise ValueError(f"Unknown template: {template_name}")
    return template_func(data)


def get_available_templates() -> list:
    """Get list of available template names."""
    return list(TEMPLATE_REGISTRY.keys())
