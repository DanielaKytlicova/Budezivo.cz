"""Pure unit tests for contact_service helpers (no DB).

The DB-dependent flows (upsert, dedup, link insertion) are verified
end-to-end via the API smoke tests run during deployment. These tests
lock the deterministic helpers so the classification / parsing logic
can't drift silently.
"""
from services.contact_service import (
    _classify_event_source,
    _split_name,
    _school_type_from_group,
    _EVENT_TYPE_MAP,
)


# ── _classify_event_source ────────────────────────────────────────────────

class _Ev:
    """Minimal stub that quacks like an Event ORM object."""
    def __init__(self, type_):
        self.type = type_


def test_classify_workshop():
    assert _classify_event_source(_Ev('workshop')) == 'workshop'


def test_classify_kurz_synonyms():
    assert _classify_event_source(_Ev('kurz')) == 'kurz'
    assert _classify_event_source(_Ev('course')) == 'kurz'


def test_classify_tabor_synonyms():
    assert _classify_event_source(_Ev('tabor')) == 'primestsky_tabor'
    assert _classify_event_source(_Ev('primestsky_tabor')) == 'primestsky_tabor'


def test_classify_baby_herna():
    assert _classify_event_source(_Ev('baby_herna')) == 'baby_herna'
    assert _classify_event_source(_Ev('babyherna')) == 'baby_herna'


def test_classify_unknown_falls_back():
    assert _classify_event_source(_Ev('vyrocni-galavecer')) == 'jednorazova_akce'
    assert _classify_event_source(_Ev(None)) == 'jednorazova_akce'
    assert _classify_event_source(_Ev('')) == 'jednorazova_akce'


def test_classify_case_insensitive():
    assert _classify_event_source(_Ev('WORKSHOP')) == 'workshop'
    assert _classify_event_source(_Ev('Tabor')) == 'primestsky_tabor'


# ── _split_name ───────────────────────────────────────────────────────────

def test_split_name_first_last():
    assert _split_name('Jana Nová') == ('Jana', 'Nová')


def test_split_name_with_titles():
    # Last token treated as surname
    assert _split_name('Mgr. Petr Hruška') == ('Mgr. Petr', 'Hruška')
    assert _split_name('PaedDr. Karel Malý') == ('PaedDr. Karel', 'Malý')


def test_split_name_single_token():
    assert _split_name('Cher') == ('Cher', None)


def test_split_name_empty_or_none():
    assert _split_name('') == (None, None)
    assert _split_name(None) == (None, None)
    assert _split_name('   ') == (None, None)


def test_split_name_extra_whitespace():
    assert _split_name('  Jana   Nová  ') == ('Jana', 'Nová')


# ── _school_type_from_group ───────────────────────────────────────────────

def test_school_type_ms():
    assert _school_type_from_group('ms') == 'MS'
    assert _school_type_from_group('MS') == 'MS'


def test_school_type_zs_variants():
    assert _school_type_from_group('zs1') == 'ZS'
    assert _school_type_from_group('zs2') == 'ZS'
    assert _school_type_from_group('zs') == 'ZS'


def test_school_type_ss_includes_gym():
    assert _school_type_from_group('ss') == 'SS'
    assert _school_type_from_group('gymnazium') == 'SS'


def test_school_type_vos_vs():
    assert _school_type_from_group('vos') == 'VOS'
    assert _school_type_from_group('vs') == 'VS'
    assert _school_type_from_group('univerzita') == 'VS'


def test_school_type_unknown():
    assert _school_type_from_group(None) is None
    assert _school_type_from_group('') is None
    assert _school_type_from_group('verejnost') is None


# ── EVENT_TYPE_MAP completeness ───────────────────────────────────────────

def test_event_type_map_has_all_documented_keys():
    """The 6 contact-source enum values must all be reachable from event types."""
    expected_targets = {'jednorazova_akce', 'workshop', 'kurz', 'primestsky_tabor', 'baby_herna'}
    actual_targets = set(_EVENT_TYPE_MAP.values())
    assert expected_targets.issubset(actual_targets), (
        f"Missing source classes: {expected_targets - actual_targets}"
    )
