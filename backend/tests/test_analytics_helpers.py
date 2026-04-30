"""Regression tests for traffic-analytics utilities (iter76).

These tests target the pure helper functions in ``routes/analytics.py``;
the pageview-recording endpoint and stats endpoint are covered by the
manual curl smoke executed by the main agent.
"""
from __future__ import annotations

import os

import pytest

from routes.analytics import (
    _is_ignorable_path,
    _is_bot,
    _ip_hash,
    _session_id,
    _normalize_ip,
    _load_admin_ips,
)


# ---------- ignorable paths ----------

@pytest.mark.parametrize("path,expected", [
    ("/", False),
    ("/akce/letni-tabor", False),
    ("/admin/dashboard", False),
    ("/login", False),
    # API
    ("/api/", True),
    ("/api/programs", True),
    # Static
    ("/static/main.js", True),
    ("/assets/logo.png", True),
    ("/favicon.ico", True),
    ("/something/file.css", True),
    ("/x.webp", True),
    ("/x.WebP", True),  # case-insensitive
    ("/x.json", True),
    # Edge cases
    ("", True),
    ("noslash", True),
    ("/path?id=1", False),  # query is fine
    ("/foo/bar.js?v=1", True),
])
def test_is_ignorable_path(path, expected):
    assert _is_ignorable_path(path) is expected


# ---------- bot detection ----------

@pytest.mark.parametrize("ua,expected", [
    ("", True),
    ("Googlebot/2.1", True),
    ("Mozilla/5.0 AhrefsBot/7.0", True),
    ("Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120 Safari/537.36", False),
    ("curl/7.81.0", True),
    ("python-requests/2.31", True),
    ("PostmanRuntime/7.32", False),  # not in our keyword list — allowed
])
def test_is_bot(ua, expected):
    assert _is_bot(ua) is expected


# ---------- IP normalization ----------

def test_normalize_ipv4():
    assert _normalize_ip("86.49.248.233") == "86.49.248.233"


def test_normalize_ipv6_collapses():
    assert _normalize_ip("2a02:8309:86:d900:6909:515f:e50e:a78f").startswith("2a02:8309:86:d900")


def test_normalize_invalid_passthrough():
    assert _normalize_ip("not-an-ip") == "not-an-ip"


# ---------- IP hash + session id ----------

def test_ip_hash_is_deterministic_per_day():
    a = _ip_hash("1.2.3.4", "2026-04-28")
    b = _ip_hash("1.2.3.4", "2026-04-28")
    assert a == b
    assert len(a) == 64


def test_ip_hash_rotates_per_day():
    a = _ip_hash("1.2.3.4", "2026-04-28")
    b = _ip_hash("1.2.3.4", "2026-04-29")
    assert a != b


def test_session_id_includes_ua():
    a = _session_id("1.2.3.4", "Chrome", "2026-04-28")
    b = _session_id("1.2.3.4", "Firefox", "2026-04-28")
    assert a != b


def test_session_id_same_visitor_same_day():
    a = _session_id("1.2.3.4", "Chrome", "2026-04-28")
    b = _session_id("1.2.3.4", "Chrome", "2026-04-28")
    assert a == b


# ---------- ADMIN_IP env ----------

def test_admin_ips_empty(monkeypatch):
    monkeypatch.delenv("ADMIN_IP", raising=False)
    assert _load_admin_ips() == set()


def test_admin_ips_csv(monkeypatch):
    monkeypatch.setenv("ADMIN_IP", "86.49.248.233 , 1.1.1.1,, 2a02:8309:86:d900:6909:515f:e50e:a78f")
    out = _load_admin_ips()
    assert "86.49.248.233" in out
    assert "1.1.1.1" in out
    # IPv6 normalization keeps the canonical form
    assert any(ip.startswith("2a02:8309:86:d900") for ip in out)


def test_admin_ips_invalid_skipped(monkeypatch):
    monkeypatch.setenv("ADMIN_IP", "1.2.3.4,not-ip,5.6.7.8")
    out = _load_admin_ips()
    assert out == {"1.2.3.4", "5.6.7.8"}
