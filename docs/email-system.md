# Email System Documentation - Budeživo.cz

## Přehled

Transakční emailový systém pro platformu Budeživo.cz. Systém je postaven na Resend API a poskytuje modulární architekturu pro odesílání emailů z různých částí aplikace.

## Architektura

```
/app/backend/
├── config/
│   └── email_config.py       # Konfigurace, sender adresy, typy emailů
├── services/
│   └── email_service.py      # Hlavní email service
├── templates/
│   └── emails/
│       ├── __init__.py       # Export šablon
│       └── templates.py      # HTML šablony emailů
├── routes/
│   └── emails.py             # API endpointy pro emaily
└── docs/
    └── email-system.md       # Tato dokumentace
```

## Typy emailů

### Account (Účet)
| Typ | Popis | Kdy se odesílá |
|-----|-------|----------------|
| `user_registration_confirmation` | Uvítací email | Po registraci nového uživatele |
| `account_activation` | Aktivační email | Po vytvoření účtu (pokud vyžaduje aktivaci) |
| `password_reset` | Reset hesla | Po žádosti o reset hesla |
| `password_changed` | Potvrzení změny hesla | Po úspěšné změně hesla |

### Reservations (Rezervace)
| Typ | Popis | Kdy se odesílá |
|-----|-------|----------------|
| `reservation_created_teacher` | Potvrzení pro učitele | Po vytvoření rezervace |
| `reservation_created_institution` | Notifikace pro instituci | Po vytvoření nové rezervace |
| `reservation_confirmed` | Potvrzení rezervace | Po potvrzení instituí |
| `reservation_rejected` | Odmítnutí rezervace | Po odmítnutí institucí |
| `reservation_updated` | Aktualizace rezervace | Po změně detailů |
| `reservation_cancelled` | Zrušení rezervace | Po zrušení |

### Reminders (Připomínky)
| Typ | Popis | Kdy se odesílá |
|-----|-------|----------------|
| `reservation_reminder_teacher` | Připomínka pro učitele | 1-2 dny před programem |
| `reservation_reminder_institution` | Připomínka pro instituci | 1 den před programem |

### Admin
| Typ | Popis | Kdy se odesílá |
|-----|-------|----------------|
| `new_institution_registration` | Nová registrace | Po registraci nové instituce |

## Sender adresy

| Typ | Adresa | Použití |
|-----|--------|---------|
| No Reply | `no-reply@budezivo.cz` | Systémové emaily |
| Reservations | `reservations@budezivo.cz` | Emaily o rezervacích |
| Accounts | `accounts@budezivo.cz` | Emaily o účtech |

## Proměnné v šablonách

Následující proměnné jsou dostupné ve všech šablonách:

```
{{institution_name}}     - Název instituce
{{institution_email}}    - Email instituce
{{institution_phone}}    - Telefon instituce
{{institution_address}}  - Adresa instituce
{{program_name}}         - Název programu
{{program_description}}  - Popis programu
{{program_duration}}     - Délka programu (min)
{{reservation_date}}     - Datum rezervace
{{reservation_time}}     - Čas rezervace
{{reservation_id}}       - ID rezervace
{{teacher_name}}         - Jméno učitele/kontaktu
{{teacher_email}}        - Email učitele
{{teacher_phone}}        - Telefon učitele
{{school_name}}          - Název školy
{{children_count}}       - Počet dětí/žáků
{{teachers_count}}       - Počet pedagogů
{{special_requirements}} - Speciální požadavky
{{user_name}}            - Jméno uživatele
{{user_email}}           - Email uživatele
{{reset_link}}           - Odkaz pro reset hesla
{{activation_link}}      - Aktivační odkaz
{{cancellation_reason}}  - Důvod zrušení
{{rejection_reason}}     - Důvod odmítnutí
{{booking_url}}          - URL rezervačního systému
{{dashboard_url}}        - URL administrace
```

## Environment Variables

```env
# Povinné
RESEND_API_KEY=re_xxxxx          # API klíč z Resend

# Volitelné
ENV=development|production        # development = přesměrování na dev email
DEV_EMAIL=dev@budezivo.cz        # Email pro development mode
SENDER_EMAIL=no-reply@budezivo.cz # Fallback sender
```

## Development Mode

Pokud `ENV=development`:
- Všechny emaily jsou přesměrovány na `DEV_EMAIL`
- Subject obsahuje původního příjemce: `[DEV - původně pro: user@example.com] ...`
- Logování obsahuje informace o přesměrování

## API Endpoints

### GET /api/emails/config
Vrátí stav konfigurace emailového systému.

```json
{
  "configured": true,
  "development_mode": false,
  "available_templates": ["user_registration_confirmation", ...],
  "sender_addresses": {...}
}
```

### GET /api/emails/templates
Seznam všech dostupných šablon.

```json
{
  "templates": [...],
  "count": 14,
  "categories": {
    "account": [...],
    "reservation": [...],
    "reminder": [...],
    "admin": [...]
  }
}
```

### GET /api/emails/templates/{template_name}
Náhled šablony s ukázkovými daty.

### GET /api/emails/variables
Seznam dostupných proměnných pro šablony.

### POST /api/emails/test
Odeslání testovacího emailu.

**Request:**
```json
{
  "email_type": "reservation_created_teacher",
  "email": "test@example.com"
}
```

**Response:**
```json
{
  "status": "sent",
  "message": "Email sent to test@example.com",
  "email_id": "abc123",
  "template_name": "reservation_created_teacher"
}
```

### GET /api/emails/logs
Historie odeslaných emailů pro aktuální instituci.

## Použití v kódu

### Odeslání transakčního emailu

```python
from services.email_service import EmailService

result = await EmailService.send_transactional_email(
    template_name="reservation_confirmed",
    to_email="teacher@school.cz",
    data={
        "teacher_name": "Jan Novák",
        "program_name": "Objevujeme malíře",
        "reservation_date": "15. 1. 2026",
        # ...další proměnné
    },
    reply_to="museum@institution.cz"
)
```

### Použití trigger funkcí

```python
from services.email_service import (
    trigger_reservation_created_emails,
    trigger_reservation_confirmed_email,
)

# Po vytvoření rezervace
results = await trigger_reservation_created_emails(
    booking_data=booking,
    program_data=program,
    institution_data=institution,
)

# Po potvrzení rezervace
result = await trigger_reservation_confirmed_email(
    booking_data=booking,
    program_data=program,
    institution_data=institution,
)
```

### Odeslání vlastního emailu

```python
from services.email_service import EmailService

result = await EmailService.send_email(
    to_email="user@example.com",
    subject="Vlastní předmět",
    html_content="<h1>HTML obsah</h1>",
    text_content="Textová verze",
    from_email="custom@budezivo.cz",
    reply_to="reply@budezivo.cz",
)
```

## Testování

### Manuální test přes API

```bash
# Test konfigurace
curl -X GET "https://api.budezivo.cz/api/emails/config"

# Odeslání testovacího emailu
curl -X POST "https://api.budezivo.cz/api/emails/test" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"email_type": "reservation_created_teacher", "email": "test@example.com"}'
```

### Preview šablony

```bash
curl -X GET "https://api.budezivo.cz/api/emails/templates/reservation_confirmed"
```

## Logování

Všechny odeslané emaily jsou logovány:
- V aplikačních logách (stdout/stderr)
- V databázi (tabulka `email_logs`)

Log entry obsahuje:
- ID emailu (z Resend)
- Příjemce
- Status (sent/failed/skipped)
- Chybová zpráva (pokud selhalo)
- Časové razítko

## Řešení problémů

### Email nebyl odeslán

1. Zkontrolujte `RESEND_API_KEY` v `.env`
2. Ověřte, že doména je verifikovaná v Resend
3. Zkontrolujte logy: `GET /api/emails/logs`
4. Ověřte development mode: `GET /api/emails/config`

### Šablona nenalezena

1. Zkontrolujte název šablony: `GET /api/emails/templates`
2. Ověřte import v `templates/emails/__init__.py`

### Proměnné nejsou nahrazeny

1. Zkontrolujte správný formát: `{{variable_name}}`
2. Ověřte, že proměnná je předána v `data` dict
3. Seznam proměnných: `GET /api/emails/variables`

## Budoucí rozšíření

- [ ] Podpora pro přílohy
- [ ] A/B testování šablon
- [ ] Statistiky doručitelnosti
- [ ] Webhook pro status updates z Resend
- [ ] Queue systém pro hromadné odesílání
- [ ] Lokalizace (EN verze šablon)
