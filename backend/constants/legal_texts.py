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



# ============ Všeobecné obchodní podmínky (VOP) ============

CURRENT_VOP_VERSION = "v1"

VOP_SECTIONS = {
    "v1": [
        {
            "number": 1,
            "title": "Úvodní ustanovení",
            "content": [
                "1.1 Tyto obchodní podmínky upravují vztah mezi:\n- Provozovatelem: Daniela Kytlicová, IČO 07407971, se sídlem Mlýnská 538 (není plátce DPH)\n- Institucí: uživatelem platformy",
                "1.2 Registrací vzniká smluvní vztah dle § 1724 a násl. zákona č. 89/2012 Sb."
            ]
        },
        {
            "number": 2,
            "title": "Předmět služby (SaaS)",
            "content": [
                "2.1 Platforma Budeživo.cz je online rezervační systém poskytovaný jako SaaS.",
                "2.2 Provozovatel poskytuje:\n- správu rezervací\n- správu klientů\n- komunikační nástroje\n- přístup do administrace",
                "2.3 Instituce získává nevýhradní licenci k užívání."
            ]
        },
        {
            "number": 3,
            "title": "Uživatelský účet",
            "content": [
                "3.1 Instituce odpovídá za správnost údajů.",
                "3.2 Instituce odpovídá za zabezpečení přístupů.",
                "3.3 Provozovatel může účet omezit při porušení podmínek."
            ]
        },
        {
            "number": 4,
            "title": "Role platformy (zásadní ustanovení)",
            "content": [
                "4.1 Platforma Budeživo.cz je pouze zprostředkovatelem (technickým nástrojem) mezi institucemi a jejich zákazníky.",
                "4.2 Provozovatel:\n- nevstupuje do smluvních vztahů mezi Institucí a zákazníkem\n- není poskytovatelem nabízených služeb\n- nenese odpovědnost za realizaci, průběh ani kvalitu služeb",
                "4.3 Veškeré závazky vznikají výhradně mezi Institucí a zákazníkem.",
                "4.4 Provozovatel nenese odpovědnost za:\n- neuskutečněné rezervace (např. nedostavení se školy)\n- storna rezervací nebo změny termínů\n- škody vzniklé mezi Institucí a zákazníkem\n- kvalitu poskytovaných služeb\n- jakékoliv nepřímé nebo následné škody"
            ]
        },
        {
            "number": 5,
            "title": "Povinnosti Instituce",
            "content": [
                "Instituce se zavazuje:\n- poskytovat pravdivé informace\n- realizovat potvrzené rezervace\n- dodržovat právní předpisy",
                "Zakazuje se:\n- zneužití systému\n- obcházení platformy\n- porušování práv třetích stran"
            ]
        },
        {
            "number": 6,
            "title": "Povinnosti Provozovatele",
            "content": [
                "Provozovatel:\n- zajišťuje provoz systému\n- může provádět údržbu\n- může upravovat funkce",
                "Nezaručuje:\n- nepřetržitý provoz\n- bezchybnost"
            ]
        },
        {
            "number": 7,
            "title": "Platební podmínky",
            "content": [
                "7.1 Platforma nabízí bezplatné i placené tarify.",
                "7.2 Placené funkce jsou aktivovány:\n- na základě zálohové faktury\n- po připsání platby",
                "7.3 Aktivace probíhá automaticky.",
                "7.4 Provozovatel není plátcem DPH.",
                "7.5 Ceny uvedené na webu jsou konečné.",
                "7.6 Platby jsou nevratné, pokud není uvedeno jinak.",
                "7.7 Při prodlení:\n- může být služba omezena",
                "7.8 Platby účastníků za akce/události jsou zpracovávány prostřednictvím platební brány třetí strany (např. Comgate). Poplatky za transakce se řídí ceníkem této brány a hradí je přímo daná instituce (příjemce platby). Provozovatel platformy není stranou platební transakce mezi účastníkem a institucí."
            ]
        },
        {
            "number": 8,
            "title": "SLA (dostupnost služby)",
            "content": [
                "8.1 Provozovatel se zavazuje k maximální možné dostupnosti.",
                "8.2 Plánované odstávky mohou probíhat:\n- mimo špičku\n- s oznámením předem",
                "8.3 Provozovatel nenese odpovědnost za výpadky způsobené:\n- třetími stranami\n- vyšší mocí"
            ]
        },
        {
            "number": 9,
            "title": "Reklamace služby",
            "content": [
                "9.1 Instituce může reklamovat funkčnost systému.",
                "9.2 Reklamace musí být podána:\n- e-mailem\n- bez zbytečného odkladu",
                "9.3 Provozovatel:\n- posoudí reklamaci\n- navrhne řešení"
            ]
        },
        {
            "number": 10,
            "title": "Ochrana osobních údajů (GDPR + DPA logika)",
            "content": [
                "10.1 Provozovatel zpracovává osobní údaje dle GDPR.",
                "10.2 Role:\n- Instituce = správce dat\n- Provozovatel = zpracovatel",
                "10.3 Provozovatel zpracovává data pouze:\n- dle pokynů Instituce\n- za účelem provozu služby",
                "10.4 Zabezpečení:\n- technická a organizační opatření\n- ochrana proti zneužití",
                "10.5 Subdodavatelé (např. hosting) mohou být zapojeni."
            ]
        },
        {
            "number": 11,
            "title": "Cookies a technická data",
            "content": [
                "11.1 Platforma používá cookies pro:\n- funkčnost\n- analytiku",
                "11.2 Používáním služby uživatel souhlasí s jejich použitím."
            ]
        },
        {
            "number": 12,
            "title": "Odpovědnost",
            "content": [
                "12.1 Provozovatel odpovídá pouze za škody způsobené úmyslně nebo hrubou nedbalostí.",
                "12.2 Neodpovídá za:\n- ušlý zisk\n- nepřímé škody\n- ztrátu dat způsobenou uživatelem",
                "12.3 Maximální odpovědnost je omezena výší plateb za posledních 12 měsíců."
            ]
        },
        {
            "number": 13,
            "title": "Doba trvání a ukončení",
            "content": [
                "13.1 Smlouva vzniká registrací.",
                "13.2 Ukončení:\n- kdykoliv uživatelem\n- při porušení podmínek",
                "13.3 Data mohou být po ukončení smazána."
            ]
        },
        {
            "number": 14,
            "title": "Změny podmínek",
            "content": [
                "14.1 Provozovatel může podmínky měnit.",
                "14.2 Změny budou oznámeny:\n- e-mailem\n- v systému"
            ]
        },
        {
            "number": 15,
            "title": "Závěrečná ustanovení",
            "content": [
                "15.1 Neplatnost části neovlivňuje celek.",
                "15.2 Řídí se právem ČR.",
                "15.3 Spory řeší soudy ČR."
            ]
        },
        {
            "number": 16,
            "title": "Ochrana systému a duševního vlastnictví",
            "content": [
                "16.1 Platforma Budeživo.cz, včetně jejího zdrojového kódu, funkční logiky, struktury, databází a uživatelského rozhraní, je chráněna jako autorské dílo a obchodní tajemství provozovatele.",
                "16.2 Instituce získává pouze nevýhradní a nepřenosné právo užívat platformu v rozsahu stanoveném těmito podmínkami.",
                "16.3 Instituce se zavazuje, že nebude:\n- kopírovat, upravovat nebo jinak reprodukovat platformu nebo její části\n- analyzovat, dekompilovat nebo se pokoušet o reverzní inženýrství systému\n- využívat platformu nebo její části za účelem vývoje nebo podpory konkurenční služby\n- systematicky získávat nebo využívat data z platformy (zejména kontakty škol) pro jiné než oprávněné účely\n- obcházet platformu za účelem přímého sjednání služeb mimo systém, pokud k navázání kontaktu došlo prostřednictvím platformy",
                "16.4 Veškerá práva k:\n- zdrojovému kódu\n- rezervační a kolizní logice\n- architektuře systému\n- designu a UX řešení\nnáleží výhradně provozovateli.",
                "16.5 V případě porušení těchto ustanovení je provozovatel oprávněn:\n- okamžitě omezit nebo ukončit přístup Instituce k platformě\n- požadovat náhradu vzniklé škody"
            ]
        }
    ]
}


def get_vop_sections(version: str = None) -> list:
    """Get VOP sections for specified version."""
    ver = version or CURRENT_VOP_VERSION
    return VOP_SECTIONS.get(ver, VOP_SECTIONS["v1"])
