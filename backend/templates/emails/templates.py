"""
Email Templates for Budeživo.cz
React Email compatible HTML templates for transactional emails.
Supports institution branding (logo + colors) via theme configuration.
"""
from typing import Dict, Any, Optional


# ============ DEFAULT STYLES ============

DEFAULT_THEME = {
    "primary_color": "#1E293B",
    "secondary_color": "#84A98C",
    "accent_color": "#E9C46A",
    "logo_url": None,
}

BASE_STYLES = {
    "container": "font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;",
    "content": "padding: 32px 24px;",
    "h1": "color: #1E293B; font-size: 24px; font-weight: 600; margin: 0 0 16px 0;",
    "h2": "color: #334155; font-size: 18px; font-weight: 600; margin: 24px 0 12px 0;",
    "text": "color: #475569; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0;",
    "info_box": "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin: 20px 0;",
    "info_label": "color: #64748B; font-size: 14px; width: 140px;",
    "info_value": "color: #1E293B; font-size: 14px; font-weight: 500;",
    "footer": "background-color: #F8FAFC; padding: 24px; text-align: center; border-top: 1px solid #E2E8F0;",
    "footer_text": "color: #64748B; font-size: 12px; line-height: 1.5; margin: 0;",
    "divider": "border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;",
    "alert_success": "background-color: #ECFDF5; border: 1px solid #10B981; border-radius: 6px; padding: 16px; color: #065F46;",
    "alert_warning": "background-color: #FFFBEB; border: 1px solid #F59E0B; border-radius: 6px; padding: 16px; color: #92400E;",
    "alert_error": "background-color: #FEF2F2; border: 1px solid #EF4444; border-radius: 6px; padding: 16px; color: #991B1B;",
}


# ============ THEME HELPERS ============

def _build_theme(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract theme configuration from template data context.
    Checks for theme_* prefixed keys first (from find_by_id_with_theme),
    then falls back to institution_logo_url, then to defaults.
    Theme is ONLY applied if a logo exists.
    """
    logo = (
        data.get("theme_logo_url")
        or data.get("institution_logo_url")
        or None
    )
    if not logo:
        return {**DEFAULT_THEME, "logo_url": None}

    return {
        "logo_url": logo,
        "primary_color": data.get("theme_primary_color") or DEFAULT_THEME["primary_color"],
        "secondary_color": data.get("theme_secondary_color") or DEFAULT_THEME["secondary_color"],
        "accent_color": data.get("theme_accent_color") or DEFAULT_THEME["accent_color"],
    }


def _button_style(theme: Dict[str, Any], variant: str = "primary") -> str:
    """Generate inline button style based on theme."""
    colors = {
        "primary": theme["primary_color"],
        "secondary": theme["secondary_color"],
        "danger": "#DC2626",
    }
    bg = colors.get(variant, theme["primary_color"])
    return (
        f"display: inline-block; background-color: {bg}; color: #ffffff; "
        f"padding: 14px 28px; text-decoration: none; border-radius: 6px; "
        f"font-weight: 500; font-size: 15px;"
    )


# ============ BUDEZIVO SVG LOGO ============

BUDEZIVO_LOGO_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 265.42 73.09" width="180" height="50">
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


# ============ BASE TEMPLATE ============

def _base_template(content: str, data: Optional[Dict[str, Any]] = None, footer_extra: str = "") -> str:
    """Wrap content in base email template.
    If data contains a valid logo (via theme), renders branded header.
    Otherwise renders the default Budeživo header.
    """
    theme = _build_theme(data or {})
    has_branding = bool(theme["logo_url"])

    if has_branding:
        header_bg = theme["secondary_color"]
        header_html = f'''
            <div style="background-color: {header_bg}; padding: 32px 24px; text-align: center;">
                <img src="{theme['logo_url']}" alt="Logo instituce"
                     style="max-height: 72px; max-width: 240px; object-fit: contain;" />
            </div>'''
    else:
        header_html = f'''
            <div style="background-color: #1E293B; padding: 24px; text-align: center;">
                {BUDEZIVO_LOGO_SVG}
            </div>'''

    # Footer: mention Budeživo as platform in branded emails
    footer_platform = ""
    if has_branding:
        footer_platform = '<br><span style="color: #94A3B8;">Rezervace přes Budeživo.cz</span>'

    return f"""<!DOCTYPE html>
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
                    {header_html}
                    <div style="{BASE_STYLES['content']}">
                        {content}
                    </div>
                    <div style="{BASE_STYLES['footer']}">
                        <p style="{BASE_STYLES['footer_text']}">
                            Tento email byl odeslán automaticky systémem Budeživo.cz<br>
                            Pokud máte dotazy, kontaktujte nás na info@budezivo.cz
                            {footer_extra}
                            {footer_platform}
                        </p>
                    </div>
                </div>
            </td>
        </tr>
    </table>
</body>
</html>"""


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


# ============ REUSABLE COMPONENTS ============

def _reservation_details_box(data: Dict[str, Any]) -> str:
    """Reusable reservation details box."""
    pricing_info = (data.get('program_pricing_info') or '').strip()
    pricing_row = ''
    if pricing_info:
        # Preserve line breaks entered by the institution
        safe = pricing_info.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        pricing_row = f"""
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">Cena:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{safe}</td>
                </tr>
"""
    return f"""
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 140px;">Program:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500;">{data.get('program_name', '')}</td>
                </tr>{pricing_row}
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


def _calendar_buttons(data: Dict[str, Any]) -> str:
    """Two side-by-side "Add to Calendar" CTA buttons (Google + Outlook web).

    Hidden gracefully when calendar URLs are missing (e.g. invalid date in
    booking_data so _compute_calendar_links returned empty strings).

    Layout: tabulka místo flex/grid, protože Outlook desktop a Gmail iOS
    flexbox/grid plně nepodporují a stále chceme dvě tlačítka vedle sebe.
    """
    google_url = (data.get("google_calendar_url") or "").strip()
    outlook_url = (data.get("outlook_calendar_url") or "").strip()
    if not google_url and not outlook_url:
        return ""

    google_btn = f"""
        <a href="{google_url}" target="_blank" rel="noopener"
           style="display: inline-block; padding: 12px 18px; background-color: #FFFFFF;
                  color: #1F2937; text-decoration: none; border-radius: 8px;
                  font-weight: 600; font-size: 14px; border: 1.5px solid #E5E7EB;
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                  white-space: nowrap;">
            <span style="color: #4285F4;">●</span>
            <span style="color: #EA4335;">●</span>
            <span style="color: #FBBC04;">●</span>
            <span style="color: #34A853;">●</span>
            &nbsp;Přidat do Google kalendáře
        </a>
    """ if google_url else ""

    outlook_btn = f"""
        <a href="{outlook_url}" target="_blank" rel="noopener"
           style="display: inline-block; padding: 12px 18px; background-color: #FFFFFF;
                  color: #1F2937; text-decoration: none; border-radius: 8px;
                  font-weight: 600; font-size: 14px; border: 1.5px solid #E5E7EB;
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                  white-space: nowrap;">
            <span style="color: #0078D4; font-weight: 700;">⊞</span>
            &nbsp;Přidat do Outlooku
        </a>
    """ if outlook_url else ""

    return f"""
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               style="margin: 24px auto 8px auto; border-collapse: collapse;">
            <tr>
                <td style="padding: 0 6px;">{google_btn}</td>
                <td style="padding: 0 6px;">{outlook_btn}</td>
            </tr>
            <tr>
                <td colspan="2" style="text-align: center; padding-top: 8px;">
                    <p style="margin: 0; font-size: 11px; color: #6B7280;
                              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">
                        Nebo otevřete přiloženou rezervaci.ics ve svém kalendářovém klientu.
                    </p>
                </td>
            </tr>
        </table>
    """


def _reservation_important_notice() -> str:
    """Important notice/disclaimer for reservation emails."""
    return """
        <div style="margin-top: 32px; padding: 16px; background-color: #F3F4F6; border-radius: 8px; text-align: center;">
            <p style="margin: 0; font-size: 12px; line-height: 1.5; color: #6B7280;">
                Budeživo.cz je pouze zprostředkovatelem rezervace a nenese odpovědnost za její realizaci.
                <a href="https://www.budezivo.cz/terms" style="color: #3B82F6; text-decoration: underline;">Více informací</a>
            </p>
        </div>
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
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}" style="{_button_style(_build_theme(data))}">
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
"""

    return {
        "subject": "Vítejte v Budeživo.cz!",
        "html": _base_template(content, data),
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
            <a href="{data.get('activation_link', '#')}" style="{_button_style(_build_theme(data))}">
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
        "html": _base_template(content, data),
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
            obdrželi jsme žádost o obnovení hesla pro účet spojený s e-mailem
            <strong>{data.get('user_email', '')}</strong>.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('reset_link', '#')}" style="{_button_style(_build_theme(data))}">
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

obdrželi jsme žádost o obnovení hesla pro účet spojený s e-mailem {data.get('user_email', '')}.

Pro obnovení hesla přejděte na tento odkaz (platný 1 hodinu):
{data.get('reset_link', '#')}

Pokud jste o obnovení hesla nežádali, tento email ignorujte.
"""

    return {
        "subject": "Obnovení hesla - Budeživo.cz",
        "html": _base_template(content, data),
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
            <strong>Heslo úspěšně změněno</strong><br>
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


# ============ RESERVATION TEMPLATES ============

def reservation_created_teacher(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher after creating reservation."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace byla přijata</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>

        <p style="{BASE_STYLES['text']}">
            děkujeme za vytvořeni rezervace v instituci <strong>{data.get('institution_name', '')}</strong>.
            Vaše rezervace byla přijata a čeká na potvrzení.
        </p>

        {_reservation_details_box(data)}

        {_calendar_buttons(data)}

        <div style="{BASE_STYLES['alert_warning']}">
            <strong>Čeká na potvrzení</strong><br>
            O potvrzení rezervace vás budeme informovat e-mailem.
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

děkujeme za vytvořeni rezervace v instituci {data.get('institution_name', '')}.

Detail rezervace:
- Program: {data.get('program_name', '')}
- Datum: {data.get('reservation_date', '')}
- Čas: {data.get('reservation_time', '')}
- Škola: {data.get('school_name', '')}
- Počet dětí: {data.get('children_count', 0)}

Vaše rezervace čeká na potvrzení.

Kontakt: {data.get('institution_email', '')} / {data.get('institution_phone', '')}
"""

    return {
        "subject": f"Rezervace přijata - {data.get('program_name', '')}",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_created_institution(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to institution after new reservation."""
    theme = _build_theme(data)

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
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}/bookings" style="{_button_style(theme)}">
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_confirmed(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when reservation is confirmed."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace potvrzena!</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>

        <div style="{BASE_STYLES['alert_success']}">
            <strong>Rezervace potvrzena</strong><br>
            Vaše rezervace v instituci {data.get('institution_name', '')} byla potvrzena.
        </div>

        {_reservation_details_box(data)}

        {_calendar_buttons(data)}

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

Dostavte se prosím 10 minut před začátkem.

{data.get('institution_name', '')}
{data.get('institution_email', '')} | {data.get('institution_phone', '')}
"""

    return {
        "subject": f"Rezervace potvrzena - {data.get('program_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_rejected(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when reservation is rejected."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace nebyla potvrzena</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>

        <div style="{BASE_STYLES['alert_error']}">
            <strong>Rezervace odmítnuta</strong><br>
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
            <a href="{data.get('booking_url', '#')}" style="{_button_style(theme, 'secondary')}">
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

Pro nalezení alternativního termínu nas kontaktujte nebo navštivte: {data.get('booking_url', '#')}
"""

    return {
        "subject": f"Rezervace odmítnuta - {data.get('program_name', '')}",
        "html": _base_template(content, data),
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_cancelled(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when reservation is cancelled."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Rezervace byla zrušena</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>

        <div style="{BASE_STYLES['alert_error']}">
            <strong>Rezervace zrušena</strong><br>
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
            <a href="{data.get('booking_url', '#')}" style="{_button_style(theme)}">
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

Pro vytvořeni nové rezervace navštivte: {data.get('booking_url', '#')}
"""

    return {
        "subject": f"Rezervace zrušena - {data.get('program_name', '')}",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_rescheduled(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent to teacher when admin changes reservation date or time."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Termín rezervace byl změněn</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('teacher_name', '')},
        </p>

        <p style="{BASE_STYLES['text']}">
            Vaše rezervace programu <strong>{data.get('program_name', '')}</strong> v instituci
            <strong>{data.get('institution_name', '')}</strong> byla přesunuta na nový termín.
        </p>

        <div style="margin: 24px 0; padding: 16px; background-color: #FEF3C7; border-radius: 8px; border-left: 4px solid #F59E0B;">
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #92400E; font-weight: 600;">Původní termín:</p>
            <p style="margin: 0; font-size: 14px; color: #78350F; text-decoration: line-through;">
                {data.get('original_date', '')} &nbsp; {data.get('original_time', '')}
            </p>
        </div>

        <div style="margin: 24px 0; padding: 16px; background-color: #D1FAE5; border-radius: 8px; border-left: 4px solid {theme['secondary_color']};">
            <p style="margin: 0 0 8px 0; font-size: 13px; color: #065F46; font-weight: 600;">Nový termín:</p>
            <p style="margin: 0; font-size: 16px; color: #064E3B; font-weight: 700;">
                {data.get('reservation_date', '')} &nbsp; {data.get('reservation_time', '')}
            </p>
        </div>

        {_reservation_details_box(data)}

        {_calendar_buttons(data)}

        <p style="{BASE_STYLES['text']}">
            V případě, že vám nový termín nevyhovuje, kontaktujte nás prosím na
            {data.get('institution_email', '')} nebo {data.get('institution_phone', '')}.
        </p>

        {_reservation_important_notice()}
    """

    plain = f"""
Termín rezervace byl změněn

Dobrý den, {data.get('teacher_name', '')},

vaše rezervace programu {data.get('program_name', '')} v instituci {data.get('institution_name', '')} byla přesunuta.

Původní termín: {data.get('original_date', '')} {data.get('original_time', '')}
Nový termín: {data.get('reservation_date', '')} {data.get('reservation_time', '')}

Detail:
- Program: {data.get('program_name', '')}
- Škola: {data.get('school_name', '')}
- Počet dětí: {data.get('children_count', 0)}

Pokud vám nový termín nevyhovuje, kontaktujte nás: {data.get('institution_email', '')} / {data.get('institution_phone', '')}
"""

    return {
        "subject": f"Zmena termínu - {data.get('program_name', '')} ({data.get('reservation_date', '')})",
        "html": _base_template(content, data),
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
            <strong>Blíží se váš program!</strong><br>
            Vaše rezervace se koná <strong>{data.get('reservation_date', '')}</strong> v <strong>{data.get('reservation_time', '')}</strong>.
        </div>

        {_reservation_details_box(data)}

        {_calendar_buttons(data)}

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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def reservation_reminder_institution(data: Dict[str, Any]) -> Dict[str, str]:
    """Reminder email sent to institution before reservation."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Nadcházející rezervace</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den,
        </p>

        <div style="{BASE_STYLES['alert_warning']}">
            <strong>Zítra máte naplánovaný program</strong>
        </div>

        {_reservation_details_box(data)}

        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('dashboard_url', 'https://www.budezivo.cz/admin')}/bookings" style="{_button_style(theme)}">
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


# ============ FEEDBACK TEMPLATES ============

def feedback_request(data: Dict[str, Any]) -> Dict[str, str]:
    """Feedback request email sent to teacher after a completed program."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Zpětná vazba</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('recipient_name', data.get('teacher_name', ''))},
        </p>

        <p style="{BASE_STYLES['text']}">
            děkujeme za návštěvu programu <strong>{data.get('program_name', '')}</strong> v instituci
            <strong>{data.get('institution_name', '')}</strong> dne {data.get('formatted_date', data.get('reservation_date', ''))}.
        </p>

        <p style="{BASE_STYLES['text']}">
            Budeme rádi, pokud si najdete chvilku na vyplnění krátkého dotazníku.
            Vaše zpětná vazba nám pomáhá zlepšovat naše programy.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('feedback_url', '#')}" style="{_button_style(theme)}">
                Vyplnit dotazník
            </a>
        </div>

        <p style="{BASE_STYLES['text']}; font-size: 14px; color: #64748B;">
            Dotazník zabere pouze 2 minuty a je zcela anonymní.
        </p>
    """

    plain = f"""
Zpětná vazba

Dobrý den, {data.get('recipient_name', data.get('teacher_name', ''))},

děkujeme za návštěvu programu {data.get('program_name', '')} v instituci {data.get('institution_name', '')} dne {data.get('formatted_date', data.get('reservation_date', ''))}.

Budeme rádi za vaši zpětnou vazbu:
{data.get('feedback_url', '#')}

Dotazník zabere pouze 2 minuty a je zcela anonymní.
"""

    return {
        "subject": f"Jak se vám líbil program {data.get('program_name', '')}?",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


def feedback_reminder(data: Dict[str, Any]) -> Dict[str, str]:
    """Feedback reminder email - sent 7 days after first request."""
    theme = _build_theme(data)

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Připomínka: zpětná vazba</h1>

        <p style="{BASE_STYLES['text']}">
            Dobrý den, {data.get('recipient_name', data.get('teacher_name', ''))},
        </p>

        <p style="{BASE_STYLES['text']}">
            před týdnem jsme vám poslali žádost o zpětnou vazbu na program
            <strong>{data.get('program_name', '')}</strong>, který jste navštívili dne {data.get('formatted_date', data.get('reservation_date', ''))}
            v instituci <strong>{data.get('institution_name', '')}</strong>.
        </p>

        <p style="{BASE_STYLES['text']}">
            Pokud jste dotazník ještě nevyplnili, budeme velmi rádi za vaši zpětnou vazbu.
            Zabere vám to pouze 2 minuty.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{data.get('feedback_url', '#')}" style="{_button_style(theme, 'secondary')}">
                Vyplnit dotazník
            </a>
        </div>

        <p style="{BASE_STYLES['text']}; font-size: 14px; color: #64748B;">
            Toto je poslední připomínka. Děkujeme za váš čas!
        </p>
    """

    plain = f"""
Připomínka: zpětná vazba

Dobrý den, {data.get('recipient_name', data.get('teacher_name', ''))},

před týdnem jsme vám poslali žádost o zpětnou vazbu na program {data.get('program_name', '')},
který jste navštívili dne {data.get('formatted_date', data.get('reservation_date', ''))} v instituci {data.get('institution_name', '')}.

Pokud jste dotazník ještě nevyplnili, budeme velmi rádi za vaši zpětnou vazbu:
{data.get('feedback_url', '#')}

Toto je poslední připomínka. Děkujeme za váš čas!
"""

    return {
        "subject": f"Připomínka: Vaše zpětná vazba na program {data.get('program_name', '')}",
        "html": _base_template(content, data),
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
        "html": _base_template(content, data),
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
            <a href="mailto:{data.get('email', '')}" style="{_button_style(_build_theme(data))}">
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


# ============ TEAM INVITATION TEMPLATE ============

def team_invitation(data: Dict[str, Any]) -> Dict[str, str]:
    """Email sent when inviting a team member to join an institution."""
    theme = _build_theme(data)

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
            <a href="{data.get('invite_link', '#')}" style="{_button_style(theme)}">
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
        "html": _base_template(content, data),
        "text": _plain_text_base(plain)
    }


# ============ TEMPLATE REGISTRY ============

def event_application_confirmation(data: Dict[str, Any]) -> Dict[str, str]:
    """Confirmation email sent to an applicant after submitting an event registration."""
    import html as _html

    event_name = data.get("event_name", "")
    applicant_name = data.get("applicant_name", "")
    institution_name = data.get("institution_name", "")
    date_label = data.get("date_label")
    is_waitlist = bool(data.get("is_waitlist"))
    status = data.get("status", "pending")
    price = data.get("price") or 0
    currency = data.get("currency", "CZK")
    variable_symbol = data.get("variable_symbol")
    payment_relevant = bool(data.get("payment_relevant"))
    is_free = bool(data.get("is_free"))
    payment_method = data.get("payment_method")
    account_number = data.get("account_number")
    bank_code = data.get("bank_code")
    account_name = data.get("account_name")

    e = lambda v: _html.escape(str(v or ""))

    if is_waitlist:
        heading = "Jste na čekací listině"
        intro = (
            f"Děkujeme za zájem o „{e(event_name)}“. Kapacita je momentálně naplněná, "
            f"a proto jsme vaši přihlášku zařadili na <strong>čekací listinu</strong>. "
            f"<strong>Zatím nemáte garantované místo</strong> — ozveme se vám, jakmile se místo uvolní."
        )
        status_label = "Čekací listina"
        alert_style = BASE_STYLES["alert_warning"]
    elif status == "confirmed":
        heading = "Registrace byla potvrzena"
        intro = f"Vaše registrace na „{e(event_name)}“ byla potvrzena. Těšíme se na vás."
        status_label = "Potvrzeno"
        alert_style = BASE_STYLES["alert_success"]
    else:
        heading = "Registrace byla přijata"
        intro = (
            f"Přijali jsme vaši registraci na „{e(event_name)}“. "
            f"Toto je potvrzení o přijetí — o definitivním potvrzení vás budeme informovat."
        )
        status_label = "Přijato (čeká na potvrzení)"
        alert_style = BASE_STYLES["alert_warning"]

    rows = [
        ("Akce", e(event_name)),
        ("Účastník", e(applicant_name)),
    ]
    if date_label:
        rows.append(("Termín", e(date_label)))
    rows.append(("Stav registrace", e(status_label)))
    if price and float(price) > 0:
        rows.append(("Cena", f"{e(price)} {e(currency)}"))
    if variable_symbol:
        rows.append(("Variabilní symbol", e(variable_symbol)))

    rows_html = ""
    for i, (label, value) in enumerate(rows):
        border = "border-top: 1px solid #E2E8F0;" if i > 0 else ""
        rows_html += f"""
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 160px; {border}">{label}:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; {border}">{value}</td>
                </tr>"""

    payment_block = ""
    free_notice = (
        f'<div style="{BASE_STYLES["alert_success"]}; margin-bottom: 20px;">Účast na akci je zdarma.</div>'
        if is_free else ""
    )
    if payment_relevant and not is_waitlist and price and float(price) > 0 and account_number:
        acc = f"{e(account_number)}/{e(bank_code)}" if bank_code else e(account_number)
        payment_block = f"""
        <div style="{BASE_STYLES['info_box']}">
            <div style="color: #6B7A8D; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">
                Platební údaje
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 6px 0; color: #64748B; width: 160px;">Účet:</td>
                    <td style="padding: 6px 0; color: #1E293B; font-weight: 500;">{acc}</td></tr>
                {f'<tr><td style="padding: 6px 0; color: #64748B;">Příjemce:</td><td style="padding: 6px 0; color: #1E293B;">{e(account_name)}</td></tr>' if account_name else ''}
                {f'<tr><td style="padding: 6px 0; color: #64748B;">Variabilní symbol:</td><td style="padding: 6px 0; color: #1E293B; font-weight: 500;">{e(variable_symbol)}</td></tr>' if variable_symbol else ''}
                <tr><td style="padding: 6px 0; color: #64748B;">Částka:</td><td style="padding: 6px 0; color: #1E293B; font-weight: 500;">{e(price)} {e(currency)}</td></tr>
            </table>
        </div>"""

    method_notice = ""
    method_notice_plain = ""
    if not is_waitlist and not is_free and price and float(price) > 0:
        if payment_method == "cash":
            method_notice = f'<div style="{BASE_STYLES["info_box"]}"><strong>Platba proběhne na místě.</strong></div>'
            method_notice_plain = "Platba proběhne na místě.\n"
        elif payment_method == "gateway":
            method_notice = f'<div style="{BASE_STYLES["info_box"]}">Platba probíhá online přes platební bránu. Po úspěšném zaplacení se vaše registrace automaticky potvrdí.</div>'
            method_notice_plain = "Platba probíhá online přes platební bránu. Po úspěšném zaplacení se registrace automaticky potvrdí.\n"

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">{heading}</h1>
        <div style="{alert_style}; margin-bottom: 20px;">{intro}</div>
        {free_notice}
        {method_notice}
        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">{rows_html}
            </table>
        </div>

        {payment_block}

        <p style="{BASE_STYLES['text']}">
            Toto je automatické potvrzení přijetí registrace od instituce <strong>{e(institution_name)}</strong>.
        </p>
    """

    plain = (
        f"{heading}\n\n"
        f"Akce: {event_name}\n"
        f"Účastník: {applicant_name}\n"
        + (f"Termín: {date_label}\n" if date_label else "")
        + f"Stav registrace: {status_label}\n"
        + ("Účast na akci je zdarma.\n" if is_free else "")
        + (method_notice_plain)
        + (f"Cena: {price} {currency}\n" if price and float(price) > 0 else "")
        + (f"Variabilní symbol: {variable_symbol}\n" if variable_symbol else "")
        + f"\nInstituce: {institution_name}\n"
    )

    return {
        "subject": f"Potvrzení registrace — {event_name}",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain),
    }



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
    "reservation_rescheduled": reservation_rescheduled,
    "reservation_reminder_teacher": reservation_reminder_teacher,
    "reservation_reminder_institution": reservation_reminder_institution,
    "feedback_request": feedback_request,
    "feedback_reminder": feedback_reminder,
    "new_institution_registration": new_institution_registration,
    "contact_form_submission": contact_form_submission,
    "team_invitation": team_invitation,
    "event_application_confirmation": event_application_confirmation,
    "join_request_received": lambda d: join_request_received(d),
    "join_request_approved": lambda d: join_request_approved(d),
    "join_request_rejected": lambda d: join_request_rejected(d),
}


# ──────────────────────────────────────────────────────────────────
# Phase 83 — institution join-request workflow emails
# ──────────────────────────────────────────────────────────────────

def join_request_received(data: Dict[str, Any]) -> Dict[str, str]:
    """Notify institution admin that a new join request has arrived."""
    institution_name = data.get("institution_name", "")
    requester_name = data.get("requester_name", "")
    requester_email = data.get("requester_email", "")
    message = data.get("message", "")
    review_url = data.get("review_url", "https://budezivo.cz/admin/team")

    message_block = ""
    if message:
        escaped = message.replace("<", "&lt;").replace(">", "&gt;")
        message_block = f"""
        <div style="{BASE_STYLES['info_box']}; border-left: 3px solid #C0AC8B;">
            <div style="color: #6B7A8D; font-size: 12px; text-transform: uppercase;
                        letter-spacing: 0.5px; margin-bottom: 6px;">
                Zpráva od žadatele
            </div>
            <div style="color: #1E293B; font-size: 14px; line-height: 1.6;">{escaped}</div>
        </div>"""

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Máte novou žádost o vstup do týmu</h1>

        <p style="{BASE_STYLES['text']}">
            Někdo žádá o přidání do týmu instituce <strong>{institution_name}</strong>.
            Jako administrátor můžete žádost schválit (a vybrat roli) nebo zamítnout.
        </p>

        <div style="{BASE_STYLES['info_box']}">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #64748B; width: 140px;">Jméno:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500;">{requester_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #64748B; border-top: 1px solid #E2E8F0;">E-mail:</td>
                    <td style="padding: 8px 0; color: #1E293B; font-weight: 500; border-top: 1px solid #E2E8F0;">{requester_email}</td>
                </tr>
            </table>
        </div>

        {message_block}

        <div style="text-align: center; margin-top: 28px;">
            <a href="{review_url}" style="{BASE_STYLES['button']}">
                Otevřít žádosti v adminu
            </a>
        </div>
    """
    plain = (
        f"Nová žádost o vstup do týmu\n\n"
        f"Instituce: {institution_name}\n"
        f"Jméno: {requester_name}\n"
        f"E-mail: {requester_email}\n"
    )
    if message:
        plain += f"\nZpráva: {message}\n"
    plain += f"\nOtevřete: {review_url}\n"
    return {
        "subject": f"Nová žádost o vstup do týmu — {institution_name}",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain),
    }


def join_request_approved(data: Dict[str, Any]) -> Dict[str, str]:
    """Notify requester that their join request was approved."""
    institution_name = data.get("institution_name", "")
    assigned_role = data.get("assigned_role", "")
    temp_password = data.get("temp_password")
    login_url = data.get("login_url", "https://budezivo.cz/login")

    role_label = {
        "admin": "Administrátor instituce", "spravce": "Administrátor instituce",
        "edukator": "Edukátor", "lektor": "Lektor",
        "pokladni": "Pokladní", "staff": "Externí lektor", "viewer": "Pouze náhled",
    }.get(assigned_role, assigned_role)

    if temp_password:
        cred_block = f"""
        <div style="{BASE_STYLES['info_box']}; background: #F4F6F9; border-left: 3px solid #16A34A;">
            <div style="color: #6B7A8D; font-size: 12px; text-transform: uppercase;
                        letter-spacing: 0.5px; margin-bottom: 10px;">
                Vaše přihlašovací údaje
            </div>
            <div style="font-family: monospace; font-size: 14px; color: #1E293B; line-height: 1.8;">
                E-mail: <strong>{data.get('email', '')}</strong><br/>
                Dočasné heslo: <strong>{temp_password}</strong>
            </div>
            <div style="color: #6B7A8D; font-size: 12px; margin-top: 12px;">
                Po prvním přihlášení si prosím heslo změňte v profilu.
            </div>
        </div>"""
    else:
        cred_block = f"""
        <div style="{BASE_STYLES['info_box']}; background: #F4F6F9;">
            <div style="color: #1E293B; font-size: 14px; line-height: 1.6;">
                Přihlaste se svými stávajícími údaji — váš účet už v systému existuje
                a byl přiřazen k této instituci.
            </div>
        </div>"""

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Vaše žádost byla schválena</h1>

        <p style="{BASE_STYLES['text']}">
            Administrátor instituce <strong>{institution_name}</strong> schválil vaši žádost
            o vstup do týmu. Byla vám přidělena role <strong>{role_label}</strong>.
        </p>

        {cred_block}

        <div style="text-align: center; margin-top: 28px;">
            <a href="{login_url}" style="{BASE_STYLES['button']}">
                Přihlásit se
            </a>
        </div>
    """
    plain = (
        f"Vaše žádost byla schválena\n\n"
        f"Instituce: {institution_name}\n"
        f"Role: {role_label}\n"
    )
    if temp_password:
        plain += f"\nDočasné heslo: {temp_password}\n"
    plain += f"\nPřihlášení: {login_url}\n"
    return {
        "subject": f"Schváleno — vstup do týmu {institution_name}",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain),
    }


def join_request_rejected(data: Dict[str, Any]) -> Dict[str, str]:
    """Notify requester that their join request was rejected."""
    institution_name = data.get("institution_name", "")
    review_note = (data.get("review_note") or "").strip()

    note_block = ""
    if review_note:
        escaped = review_note.replace("<", "&lt;").replace(">", "&gt;")
        note_block = f"""
        <div style="{BASE_STYLES['info_box']}; border-left: 3px solid #B85C5C;">
            <div style="color: #6B7A8D; font-size: 12px; text-transform: uppercase;
                        letter-spacing: 0.5px; margin-bottom: 6px;">
                Poznámka od administrátora
            </div>
            <div style="color: #1E293B; font-size: 14px; line-height: 1.6;">{escaped}</div>
        </div>"""

    content = f"""
        <h1 style="{BASE_STYLES['h1']}">Vaše žádost nebyla schválena</h1>

        <p style="{BASE_STYLES['text']}">
            Administrátor instituce <strong>{institution_name}</strong> bohužel vaši žádost
            o vstup do týmu neschválil.
        </p>

        {note_block}

        <p style="{BASE_STYLES['text']}">
            Pokud máte za to, že jde o nedorozumění, kontaktujte prosím administrátora
            instituce přímo, nebo nám napište na
            <a href="mailto:info@budezivo.cz" style="color: #303E4F;">info@budezivo.cz</a>.
        </p>
    """
    plain = (
        f"Vaše žádost nebyla schválena\n\n"
        f"Instituce: {institution_name}\n"
    )
    if review_note:
        plain += f"\nPoznámka: {review_note}\n"
    plain += "\nKontakt: info@budezivo.cz\n"
    return {
        "subject": f"Žádost o vstup do týmu — neschválena ({institution_name})",
        "html": _base_template(content, data),
        "text": _plain_text_base(plain),
    }

def waitlist_confirmation(data: Dict[str, Any]) -> Dict[str, str]:
    """Confirmation email for waitlist entry."""
    program_name = data.get('program_name', 'Program')
    teacher_name = data.get('teacher_name', '')
    request_type = data.get('request_type', 'specific_date')
    participant_count = data.get('participant_count', 1)

    time_labels = {'morning': 'Dopoledne', 'midday': 'Kolem poledne', 'afternoon': 'Odpoledne', 'any': 'Kdykoliv'}
    preferred = time_labels.get(data.get('preferred_time', 'any'), 'Kdykoliv')

    if request_type == 'specific_date':
        date_info = f"Konkrétní datum: <strong>{data.get('requested_date', '')}</strong>"
    else:
        date_info = f"Období: <strong>{data.get('range_start_date', '')} – {data.get('range_end_date', '')}</strong>"

    return {
        'subject': f"Potvrzení zájmu o termín: {program_name}",
        'html': f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #F8FAFC;">
            <div style="background: {theme['primary']}; padding: 24px; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 20px;">Potvrzení zájmu o termín</h1>
            </div>
            <div style="padding: 24px; background: white; border: 1px solid #E2E8F0; border-top: none; border-radius: 0 0 8px 8px;">
                <p style="color: #475569; font-size: 15px;">
                    Dobrý den, {teacher_name},
                </p>
                <p style="color: #475569; font-size: 15px;">
                    zařadili jsme vás mezi zájemce o program <strong>{program_name}</strong>. Jakmile se uvolní vhodný termín, dáme vám vědět.
                </p>
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <p style="margin: 4px 0; color: #334155; font-size: 14px;">
                        <strong>Program:</strong> {program_name}
                    </p>
                    <p style="margin: 4px 0; color: #334155; font-size: 14px;">
                        {date_info}
                    </p>
                    <p style="margin: 4px 0; color: #334155; font-size: 14px;">
                        <strong>Preferovaný čas:</strong> {preferred}
                    </p>
                    <p style="margin: 4px 0; color: #334155; font-size: 14px;">
                        <strong>Počet žáků:</strong> {participant_count}
                    </p>
                </div>
                <p style="color: #64748B; font-size: 13px;">
                    Pokud se situace změní, nemusíte nic dělat — váš zájem automaticky vyprší po uplynutí zvoleného období.
                </p>
                <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 20px 0;">
                <p style="color: #94A3B8; font-size: 12px; text-align: center;">
                    Odesláno systémem Budeživo.cz
                </p>
            </div>
        </div>
        """
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
