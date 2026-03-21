"""
Legal texts and terms for Budeživo.cz platform.
Versioned for compliance and audit purposes.
"""

# Current version of legal texts
CURRENT_TERMS_VERSION = "v1"

# Liability disclaimer text shown in reservation form
RESERVATION_TERMS_CHECKBOX_TEXT = {
    "v1": "Odesláním rezervace beru na vědomí, že Budezivo.cz je pouze zprostředkovatelem rezervace a nenese odpovědnost za její realizaci."
}

# Email footer disclaimer text
RESERVATION_EMAIL_DISCLAIMER = {
    "v1": """
Důležité informace

Rezervace byla vytvořena prostřednictvím rezervačního systému Budezivo.cz, který slouží pouze jako technický nástroj pro zprostředkování rezervací mezi institucí a objednatelem.

Samotná realizace programu a podmínky účasti jsou plně v kompetenci dané instituce.

Provozovatel systému Budezivo.cz nenese odpovědnost za:
• změny nebo zrušení rezervace,
• průběh programu,
• ani za to, že se účastníci na rezervovaný program nedostaví.
"""
}

# Full terms of use document
TERMS_OF_USE = {
    "v1": {
        "title": "Podmínky používání platformy",
        "last_updated": "2026-03-21",
        "articles": [
            {
                "number": 1,
                "title": "Úvodní ustanovení",
                "content": """
Tyto Podmínky používání upravují práva a povinnosti uživatelů rezervačního systému Budeživo.cz (dále jen „Platforma").

Provozovatelem Platformy je společnost Budeživo s.r.o., se sídlem v České republice (dále jen „Provozovatel").

Používáním Platformy uživatel vyjadřuje souhlas s těmito Podmínkami.
"""
            },
            {
                "number": 2,
                "title": "Definice pojmů",
                "content": """
„Instituce" – kulturní, vzdělávací nebo jiná organizace, která prostřednictvím Platformy nabízí své programy.

„Objednatel" – škola, pedagog nebo jiná osoba, která si prostřednictvím Platformy rezervuje program.

„Program" – vzdělávací nebo doprovodný program nabízený institucí.

„Rezervace" – závazná objednávka programu vytvořená prostřednictvím Platformy.
"""
            },
            {
                "number": 3,
                "title": "Registrace a uživatelský účet",
                "content": """
Pro používání administračních funkcí Platformy je nutná registrace.

Uživatel je povinen uvést pravdivé a úplné údaje.

Uživatel odpovídá za bezpečnost svého přístupového hesla.
"""
            },
            {
                "number": 4,
                "title": "Vytváření a správa rezervací",
                "content": """
Instituce může prostřednictvím Platformy spravovat své programy a přijímat rezervace.

Objednatel může vytvářet rezervace v souladu s dostupností programů.

Potvrzení nebo odmítnutí rezervace je plně v kompetenci instituce.
"""
            },
            {
                "number": 5,
                "title": "Práva a povinnosti instituce",
                "content": """
Instituce je povinna udržovat aktuální informace o svých programech.

Instituce odpovídá za realizaci potvrzených rezervací.

Instituce je povinna dodržovat platnou legislativu, včetně GDPR.
"""
            },
            {
                "number": 6,
                "title": "Práva a povinnosti objednatele",
                "content": """
Objednatel je povinen uvést pravdivé kontaktní údaje.

Objednatel se zavazuje dostavit se na potvrzenou rezervaci nebo ji včas zrušit.

Objednatel bere na vědomí podmínky zrušení stanovené institucí.
"""
            },
            {
                "number": 7,
                "title": "Ochrana osobních údajů",
                "content": """
Provozovatel zpracovává osobní údaje v souladu s GDPR.

Podrobnosti jsou uvedeny v Zásadách ochrany osobních údajů.

Uživatel má právo na přístup, opravu a výmaz svých údajů.
"""
            },
            {
                "number": 8,
                "title": "Omezení odpovědnosti provozovatele",
                "content": """
Provozovatel neodpovídá za obsah programů nabízených institucemi.

Provozovatel neodpovídá za škody způsobené výpadkem Platformy.

Provozovatel neodpovídá za spory mezi institucí a objednatelem.
"""
            },
            {
                "number": 9,
                "title": "Změny podmínek",
                "content": """
Provozovatel si vyhrazuje právo změnit tyto Podmínky.

O změnách budou uživatelé informováni prostřednictvím Platformy.

Pokračováním v používání Platformy uživatel souhlasí se změnami.
"""
            },
            {
                "number": 10,
                "title": "Odpovědnost za realizaci rezervací",
                "content": """
Provozovatel platformy poskytuje výhradně technické řešení pro evidenci a správu rezervací vzdělávacích programů.

Provozovatel platformy:
• nevystupuje jako smluvní strana mezi institucí a školou či jiným objednatelem programu,
• neodpovídá za uzavření, změnu ani zrušení rezervace mezi těmito subjekty,
• nenese odpovědnost za skutečné uskutečnění rezervovaného programu.

Instituce bere na vědomí, že:
• rezervace vytvořená prostřednictvím platformy nepředstavuje závazek Provozovatele platformy k jejímu plnění,
• Provozovatel platformy nenese odpovědnost za to, že se škola, pedagog nebo jiný účastník na rezervovaný program nedostaví,
• Provozovatel platformy nenese odpovědnost za případné škody vzniklé v důsledku neúčasti účastníků na rezervovaném programu.

Veškeré smluvní vztahy vznikají přímo mezi institucí a objednatelem programu.
"""
            },
            {
                "number": 11,
                "title": "Závěrečná ustanovení",
                "content": """
Tyto Podmínky se řídí právním řádem České republiky.

V případě sporu je příslušný soud v České republice.

Podmínky nabývají účinnosti dnem jejich zveřejnění na Platformě.
"""
            }
        ]
    }
}


def get_current_terms_text() -> dict:
    """Get the current version of terms of use."""
    return TERMS_OF_USE.get(CURRENT_TERMS_VERSION, TERMS_OF_USE["v1"])


def get_reservation_checkbox_text(version: str = None) -> str:
    """Get reservation terms checkbox text for specified version."""
    ver = version or CURRENT_TERMS_VERSION
    return RESERVATION_TERMS_CHECKBOX_TEXT.get(ver, RESERVATION_TERMS_CHECKBOX_TEXT["v1"])


def get_email_disclaimer(version: str = None) -> str:
    """Get email disclaimer text for specified version."""
    ver = version or CURRENT_TERMS_VERSION
    return RESERVATION_EMAIL_DISCLAIMER.get(ver, RESERVATION_EMAIL_DISCLAIMER["v1"])
