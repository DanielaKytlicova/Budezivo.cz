"""Classify raw collision/availability messages into a structured object.
Keeps collision_service.py untouched while giving the frontend a localised,
code-based response it can render as tooltips or inline hints."""
from typing import Optional

_MAPPING = [
    # (needle, code, source, public_cs)
    ("Kolize místnosti", "ROOM_TAKEN", "room",
     "V tomto čase je obsazen prostor."),
    ("Kolize lektora", "LECTURER_BUSY", "lecturer",
     "V tomto čase není dostupný lektor."),
    ("Lektor není dostupný", "LECTURER_BUSY", "lecturer",
     "V tomto čase není dostupný lektor."),
    ("Lektor má blokaci", "LECTURER_BUSY", "lecturer",
     "V tomto čase není dostupný lektor."),
    ("Lektor má jednorázovou nedostupnost", "LECTURER_BUSY", "lecturer",
     "V tomto čase není dostupný lektor."),
    ("Kolize programů: Program nelze", "SEPARATE_ONLY", "separate_only",
     "Tento program může probíhat pouze samostatně."),
    ("Kolize programů: Program", "PROGRAM_BLOCKS_OTHERS", "full_block",
     "V době konání nemohou probíhat jiné programy."),
    ("Časový konflikt", "FULL_BLOCK", "full_block",
     "V tomto čase je obsazen jiný program."),
    ("Slot je jednorázově uzavřen", "EXCEPTION", "exception",
     "Tento termín je výjimečně uzavřen."),
    ("Není k dispozici žádný hlavní lektor", "NO_LECTURER_AVAILABLE", "lecturer",
     "Pro tento termín není k dispozici žádný hlavní lektor."),
]


def classify(msg: Optional[str]) -> dict:
    """Return a structured verdict: {blocked, code, source, message_cs, details}."""
    if not msg:
        return {"blocked": False, "code": "none", "source": None,
                "message_cs": "", "details": {}}
    for needle, code, source, public in _MAPPING:
        if needle in msg:
            return {
                "blocked": True, "code": code, "source": source,
                "message_cs": public, "details": {"raw": msg},
            }
    return {"blocked": True, "code": "UNKNOWN", "source": None,
            "message_cs": "Slot je obsazen.", "details": {"raw": msg}}
