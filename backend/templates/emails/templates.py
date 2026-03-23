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


def _base_template(content: str, footer_extra: str = "", institution_logo_url: str = None) -> str:
    """Wrap content in base email template. Optionally shows institution logo in header."""
    # SVG logo pro Budezivo.cz
    budezivo_logo = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 265.42 73.09" width="180" height="50">
        <style>.e-blue{fill:#5a7aae;}.e-gold{fill:#c5ac87;}</style>
        <path class="e-blue" d="M41.23,40.83a5.17,5.17,0,0,0-2.42-.69V39.9a5.64,5.64,0,0,0,2.1-.88,4.54,4.54,0,0,0,1.43-1.62,4.61,4.61,0,0,0,.52-2.22A5,5,0,0,0,42,32.29a5.43,5.43,0,0,0-2.48-1.94,10.42,10.42,0,0,0-4.09-.7h-9V51.48h9.73a9.64,9.64,0,0,0,4.12-.8,6,6,0,0,0,2.57-2.16,5.69,5.69,0,0,0,.88-3.14A5.26,5.26,0,0,0,43,42.64,5,5,0,0,0,41.23,40.83Zm-9.65-7h3.09a3.28,3.28,0,0,1,2.13.64,2.13,2.13,0,0,1,.79,1.75,2.28,2.28,0,0,1-.39,1.34,2.58,2.58,0,0,1-1.07.84,4,4,0,0,1-1.54.29h-3Zm5.91,12.85a4,4,0,0,1-2.57.67H31.58V42H35a4.12,4.12,0,0,1,1.76.34,2.67,2.67,0,0,1,1.14,1,2.75,2.75,0,0,1,.39,1.48A2.22,2.22,0,0,1,37.49,46.63Z"/>
        <path class="e-blue" d="M56.91,44.44a3.48,3.48,0,0,1-.35,1.64,2.5,2.5,0,0,1-1,1,2.91,2.91,0,0,1-1.47.36,2.51,2.51,0,0,1-2-.79,3.06,3.06,0,0,1-.71-2.16V35.1H46.34V45.53a7.09,7.09,0,0,0,.7,3.24,5.21,5.21,0,0,0,2,2.15,5.77,5.77,0,0,0,3,.76,4.82,4.82,0,0,0,3.43-1.19,6.67,6.67,0,0,0,1.69-2.59l.08,3.58H62V35.1H56.91Z"/>
        <path class="e-blue" d="M76.05,37.91h-.12a5.3,5.3,0,0,0-.9-1.44,4.65,4.65,0,0,0-1.52-1.13,5,5,0,0,0-2.22-.45,6.08,6.08,0,0,0-3.21.9,6.46,6.46,0,0,0-2.4,2.77,10.8,10.8,0,0,0-.91,4.74A10.81,10.81,0,0,0,65.65,48,6.4,6.4,0,0,0,68,50.77a6,6,0,0,0,3.31.94,5.07,5.07,0,0,0,2.16-.42A4.79,4.79,0,0,0,75,50.22a5.33,5.33,0,0,0,.93-1.4h.18v2.66h5V29.65h-5.1Zm-.25,7.72a3.54,3.54,0,0,1-1.06,1.55,2.66,2.66,0,0,1-1.67.55,2.59,2.59,0,0,1-1.66-.55,3.4,3.4,0,0,1-1-1.56A6.86,6.86,0,0,1,70,43.3,6.78,6.78,0,0,1,70.38,41a3.38,3.38,0,0,1,1-1.54,2.54,2.54,0,0,1,1.66-.55,2.65,2.65,0,0,1,1.67.54A3.33,3.33,0,0,1,75.8,41a7.78,7.78,0,0,1,0,4.68Z"/>
        <path class="e-blue" d="M97.65,37a6.9,6.9,0,0,0-2.51-1.61A9,9,0,0,0,92,34.89,8.44,8.44,0,0,0,87.69,36a7.23,7.23,0,0,0-2.8,3,9.44,9.44,0,0,0-1,4.42,9.63,9.63,0,0,0,1,4.52,6.9,6.9,0,0,0,2.85,2.91,9.16,9.16,0,0,0,4.42,1,10.13,10.13,0,0,0,3.53-.57,6.65,6.65,0,0,0,2.53-1.62,5.8,5.8,0,0,0,1.41-2.45l-4.55-.75a2.55,2.55,0,0,1-.61.93,2.68,2.68,0,0,1-1,.57,4,4,0,0,1-1.25.19,3.5,3.5,0,0,1-1.74-.42,2.87,2.87,0,0,1-1.17-1.26A4.54,4.54,0,0,1,89,44.53H99.87V43.24a10.16,10.16,0,0,0-.58-3.59A7.26,7.26,0,0,0,97.65,37ZM89,41.56a4.46,4.46,0,0,1,.3-1.27,2.87,2.87,0,0,1,1-1.25A3.1,3.1,0,0,1,92,38.6a3,3,0,0,1,1.67.44,2.74,2.74,0,0,1,1,1.26A4.67,4.67,0,0,1,95,41.56Z"/>
        <path class="e-blue" d="M200.58,46.32a2.71,2.71,0,0,0-2,.78,2.78,2.78,0,0,0,0,3.9,2.88,2.88,0,0,0,3.94,0,2.78,2.78,0,0,0,0-3.9A2.71,2.71,0,0,0,200.58,46.32Z"/>
        <path class="e-blue" d="M217.66,46.27a3.33,3.33,0,0,1-.6.88,2.44,2.44,0,0,1-.82.54,2.73,2.73,0,0,1-1,.18,2.56,2.56,0,0,1-1.67-.55,3.35,3.35,0,0,1-1.05-1.57,7.4,7.4,0,0,1-.36-2.43,7.32,7.32,0,0,1,.36-2.43,3.24,3.24,0,0,1,1.05-1.55,2.61,2.61,0,0,1,1.67-.54,2.8,2.8,0,0,1,1,.18,2.24,2.24,0,0,1,.8.53,3,3,0,0,1,.59.85A4.49,4.49,0,0,1,218,41.5l4.71-.79a6.6,6.6,0,0,0-.8-2.41,5.82,5.82,0,0,0-1.59-1.83A7.23,7.23,0,0,0,218,35.3a9.66,9.66,0,0,0-2.87-.41A8.78,8.78,0,0,0,210.75,36a7.23,7.23,0,0,0-2.84,3,10.38,10.38,0,0,0,0,8.85,7.17,7.17,0,0,0,2.84,3,8.67,8.67,0,0,0,4.41,1.06,9.46,9.46,0,0,0,2.88-.41,7.1,7.1,0,0,0,2.29-1.18,6.36,6.36,0,0,0,1.59-1.87,7.18,7.18,0,0,0,.8-2.47L218,45.09A4.53,4.53,0,0,1,217.66,46.27Z"/>
        <polygon class="e-blue" points="231.66 47.48 231.66 47.37 238.73 38.33 238.73 35.1 225.25 35.1 225.25 39.1 232.64 39.1 232.64 39.2 225 48.53 225 51.48 239.01 51.48 239.01 47.48 231.66 47.48"/>
        <path class="e-blue" d="M181.38,19.53h-35.8l-4.43,5h40.23A4.26,4.26,0,0,1,185.43,29v23.9a4.26,4.26,0,0,1-4.05,4.44H116a4.26,4.26,0,0,1-4-4.44V29a4.26,4.26,0,0,1,4-4.44h11.55l3.61-5H116A9.26,9.26,0,0,0,107,29v23.9a9.27,9.27,0,0,0,9,9.44h65.38a9.27,9.27,0,0,0,9.05-9.44V29A9.26,9.26,0,0,0,181.38,19.53Z"/>
        <polygon class="e-gold" points="119.77 48.53 119.77 51.48 133.78 51.48 133.78 47.48 126.42 47.48 126.42 47.37 133.5 38.33 133.5 35.1 120.02 35.1 120.02 39.1 127.41 39.1 127.41 39.2 119.77 48.53"/>
        <path class="e-gold" d="M141.6,29a2.66,2.66,0,0,0-1.87-.72,2.61,2.61,0,0,0-1.86.72,2.33,2.33,0,0,0,0,3.48,2.58,2.58,0,0,0,1.86.73,2.66,2.66,0,0,0,1.87-.72,2.28,2.28,0,0,0,.78-1.73A2.31,2.31,0,0,0,141.6,29Z"/>
        <rect class="e-gold" x="137.18" y="35.1" width="5.11" height="16.38"/>
        <path class="e-gold" d="M162.13,35.1h-5.34l-2.4,8c-.32,1.08-.6,2.19-.84,3.3-.09.41-.18.84-.26,1.27-.09-.43-.19-.86-.28-1.27-.24-1.13-.53-2.23-.86-3.3l-2.45-8h-5.39l5.94,16.38h5.91Z"/>
        <path class="e-gold" d="M166.74,50.72a9.7,9.7,0,0,0,8.82,0,7.08,7.08,0,0,0,2.83-3,10.48,10.48,0,0,0,0-8.85,7.14,7.14,0,0,0-2.83-3,9.7,9.7,0,0,0-8.82,0,7.21,7.21,0,0,0-2.83,3,10.38,10.38,0,0,0,0,8.85A7.15,7.15,0,0,0,166.74,50.72Zm1.74-9.79a3.41,3.41,0,0,1,1-1.57,2.73,2.73,0,0,1,3.31,0,3.41,3.41,0,0,1,1,1.57,8.54,8.54,0,0,1,0,4.77,3.46,3.46,0,0,1-1,1.6,2.69,2.69,0,0,1-3.31,0,3.46,3.46,0,0,1-1-1.6,8.3,8.3,0,0,1,0-4.77Z"/>
        <polygon class="e-gold" points="126.8 30.85 124.7 28.39 120.38 28.39 120.38 28.39 120.38 28.48 120.38 28.48 124.94 32.99 128.64 32.99 133.2 28.48 136.69 24.53 141.12 19.53 148.87 10.78 141.58 10.78 135.27 19.53 131.66 24.53 128.88 28.39 126.8 30.85"/>
    </svg>'''
    
    # Build header with optional institution logo
    if institution_logo_url:
        header_content = f'''
            <div style="text-align: center; margin-bottom: 16px;">
                <img src="{institution_logo_url}" alt="Logo instituce" style="max-height: 60px; max-width: 200px; object-fit: contain;" />
            </div>
            <div style="text-align: center; opacity: 0.7;">
                {budezivo_logo}
            </div>
        '''
    else:
        header_content = budezivo_logo
    
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
                        {header_content}
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
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}" style="{BASE_STYLES['button']}">
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

Váš účet byl úspěšně vytvořen. Přihlaste se zde: {data.get('dashboard_url', 'https://www.budezivo.cz/admin')}

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


def _reservation_important_notice() -> str:
    """Important notice/disclaimer for reservation emails - shortened version."""
    return f"""
        <div style="margin-top: 32px; padding: 16px; background-color: #F3F4F6; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #6B7280;">
                Budezivo.cz je pouze zprostředkovatelem rezervace a nenese odpovědnost za její realizaci. 
                <a href="https://www.budezivo.cz/terms" style="color: #3B82F6; text-decoration: underline;">Více informací</a>
            </p>
        </div>
    """


def reservation_created_teacher(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher after creating reservation."""
    institution_logo = data.get('institution_logo_url')
    
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
        
        {_reservation_important_notice()}
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

Vaše rezervace čeká na potvrzení.

Kontakt: {data.get('institution_email', '')} / {data.get('institution_phone', '')}

---
Budezivo.cz je pouze zprostředkovatelem rezervace. Více: https://www.budezivo.cz/terms
"""
    
    return {
        "subject": f"Rezervace přijata - {data.get('program_name', '')}",
        "html": _base_template(content, institution_logo_url=institution_logo),
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
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}/bookings" style="{BASE_STYLES['button']}">
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

Přejděte do administrace pro potvrzení: {data.get('dashboard_url', 'https://www.budezivo.cz/admin')}/bookings
"""
    
    return {
        "subject": f"Nová rezervace - {data.get('school_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


def reservation_confirmed(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when reservation is confirmed."""
    institution_logo = data.get('institution_logo_url')
    
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
        
        <p style="{BASE_STYLES['text']}">
            Dostavte se prosím 10 minut před začátkem. V případě nemoci nás kontaktujte 2 dny předem.
        </p>
        
        <p style="{BASE_STYLES['text']}">
            Těšíme se na vaši návštěvu!
        </p>
        
        <p style="{BASE_STYLES['text']}">
            <strong>{data.get('institution_name', '')}</strong><br>
            {data.get('institution_address', '')}<br>
            {data.get('institution_email', '')} | {data.get('institution_phone', '')}
        </p>
        
        {_reservation_important_notice()}
    """
    
    plain = f"""
Rezervace potvrzena!

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace v instituci {data.get('institution_name', '')} byla potvrzena.

Detail:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}

Dostavte se prosím 10 minut před začátkem. V případě nemoci nás kontaktujte 2 dny předem.

Těšíme se na vaši návštěvu!

{data.get('institution_name', '')}
{data.get('institution_email', '')} | {data.get('institution_phone', '')}

---
Budezivo.cz je pouze zprostředkovatelem rezervace. Více: https://www.budezivo.cz/terms
"""
    
    return {
        "subject": f"✓ Rezervace potvrzena - {data.get('program_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content, institution_logo_url=institution_logo),
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
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}/bookings" style="{BASE_STYLES['button']}">
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


def contact_form_submission(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when someone submits contact/demo form."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Nová poptávka z webu</h1>
        
        <p style="{BASE_STYLES['text']}">
            Někdo vyplnil kontaktní formulář na webu Budeživo.cz.
        </p>
        
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="{BASE_STYLES['info_label']}; padding: 12px 0;">Jméno:</td>
                    <td style="{BASE_STYLES['info_value']}; padding: 12px 0;">{data.get('name', '-')}</td>
                </tr>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="{BASE_STYLES['info_label']}; padding: 12px 0;">Instituce:</td>
                    <td style="{BASE_STYLES['info_value']}; padding: 12px 0;">{data.get('institution', '-')}</td>
                </tr>
                <tr style="border-bottom: 1px solid #E2E8F0;">
                    <td style="{BASE_STYLES['info_label']}; padding: 12px 0;">E-mail:</td>
                    <td style="{BASE_STYLES['info_value']}; padding: 12px 0;">
                        <a href="mailto:{data.get('email', '')}" style="color: #1E293B;">{data.get('email', '-')}</a>
                    </td>
                </tr>
                <tr>
                    <td style="{BASE_STYLES['info_label']}; padding: 12px 0;">Dostupnost:</td>
                    <td style="{BASE_STYLES['info_value']}; padding: 12px 0;">{data.get('availability', '-')}</td>
                </tr>
            </table>
        </div>
        
        <p style="{BASE_STYLES['text']}">
            <strong>Zdroj:</strong> {data.get('source', 'Kontaktní formulář')}
        </p>
        
        <hr style="{BASE_STYLES['divider']}">
        
        <p style="text-align: center;">
            <a href="mailto:{data.get('email', '')}" style="{BASE_STYLES['button']}">
                Odpovědět
            </a>
        </p>
    """
    
    plain = f"""
Nová poptávka z webu Budeživo.cz
================================

Jméno: {data.get('name', '-')}
Instituce: {data.get('institution', '-')}
E-mail: {data.get('email', '-')}
Dostupnost: {data.get('availability', '-')}
Zdroj: {data.get('source', 'Kontaktní formulář')}
"""
    
    return {
        "subject": f"Nová poptávka: {data.get('institution', 'Neznámá instituce')}",
        "html": _base_template(content),
        "text": _plain_text_base(plain)
    }


# ============ TEAM INVITATION TEMPLATE ============

def team_invitation(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when inviting a team member to join an institution."""
    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Pozvánka do týmu</h1>
        
        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('invitee_name', '')},
        </p>
        
        <p style="{BASE_STYLES['text']}">
            <strong>{data.get('inviter_name', '')}</strong> vás zve, abyste se připojili k týmu instituce 
            <strong>{data.get('institution_name', '')}</strong> v systému Budeživo.cz.
        </p>
        
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 140px;">Instituce:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500;">{data.get('institution_name', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Vaše role:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('role_name', '')}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Platnost:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{data.get('expires_hours', 48)} hodin</td>
                </tr>
            </table>
        </div>
        
        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('invite_link', '#')}" style="{BASE_STYLES['button']}">
                Přijmout pozvánku
            </a>
        </div>
        
        <p style="{BASE_STYLES['text']}; font-size: 13px; color: #64748B;">
            Pokud tlačítko nefunguje, zkopírujte tento odkaz do prohlížeče:<br>
            <a href="{data.get('invite_link', '#')}" style="color: #1E293B; word-break: break-all;">
                {data.get('invite_link', '#')}
            </a>
        </p>
        
        <hr style="{BASE_STYLES['divider']}">
        
        <p style="{BASE_STYLES['text']}; font-size: 13px; color: #64748B;">
            Pokud jste tuto pozvánku neočekávali, můžete tento email ignorovat.
        </p>
    """
    
    plain = f"""
Pozvánka do týmu - Budeživo.cz

Dobrý den, {data.get('invitee_name', '')},

{data.get('inviter_name', '')} vás zve, abyste se připojili k týmu instituce {data.get('institution_name', '')} v systému Budeživo.cz.

Vaše role: {data.get('role_name', '')}
Platnost pozvánky: {data.get('expires_hours', 48)} hodin

Pro přijetí pozvánky přejděte na tento odkaz:
{data.get('invite_link', '#')}

Pokud jste tuto pozvánku neočekávali, můžete tento email ignorovat.
"""
    
    return {
        "subject": f"Pozvánka do týmu - {data.get('institution_name', 'Budeživo.cz')}",
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
    "contact_form_submission": contact_form_submission,
    "team_invitation": team_invitation,
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
