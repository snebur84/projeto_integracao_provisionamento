import os
import sys
import types
import pytest
from django.test import RequestFactory
from django.template import TemplateSyntaxError

import api.views as views


@pytest.fixture
def rf():
    return RequestFactory()


def test_normalize_mac_various():
    assert views._normalize_mac(None) == ""
    assert views._normalize_mac("") == ""
    assert views._normalize_mac("AA:BB:CC:11:22:33") == "aabbcc112233"
    assert views._normalize_mac("aabb-cc11-2233") == "aabbcc112233"
    assert views._normalize_mac("  AA BB CC  ") == "aabbcc"


def test_parse_user_agent_success(rf):
    req = rf.get("/", HTTP_USER_AGENT="Vendor Model 1.0 00:11:22:33:44:55")
    parsed = views.parse_user_agent(req)
    assert parsed == ("Vendor", "Model", "1.0", "00:11:22:33:44:55")


def test_parse_user_agent_too_short(rf, caplog):
    req = rf.get("/", HTTP_USER_AGENT="short")
    assert views.parse_user_agent(req) is None
    assert "User-Agent parsing failed" in caplog.text


def test_is_private_ip():
    assert views._is_private_ip("10.0.0.1") is True
    assert views._is_private_ip("192.168.0.5") is True
    assert views._is_private_ip("8.8.8.8") is False
    assert views._is_private_ip("not-an-ip") is False


def test_extract_public_ip_prefers_non_private(rf):
    req = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.1, 8.8.8.8", REMOTE_ADDR="1.2.3.4")
    assert views._extract_public_ip(req) == "8.8.8.8"

    req2 = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.1, invalid", REMOTE_ADDR="1.2.3.4")
    assert views._extract_public_ip(req2) == "1.2.3.4"


def test_extract_public_ip_invalids(rf):
    req = rf.get("/", REMOTE_ADDR="not-an-ip")
    assert views._extract_public_ip(req) is None


def test_extract_private_ip_from_headers(rf):
    req = rf.get("/", HTTP_X_PRIVATE_IP="192.168.1.10,8.8.8.8")
    assert views._extract_private_ip(req) == "192.168.1.10"

    # fallback to X-Forwarded-For private
    req2 = rf.get("/", HTTP_X_FORWARDED_FOR="10.0.0.5,8.8.8.8")
    assert views._extract_private_ip(req2) == "10.0.0.5"


def test_sanitize_filename_basic():
    assert views._sanitize_filename(None) is None
    assert views._sanitize_filename("safe-file.txt") == "safe-file.txt"
    assert views._sanitize_filename("/path/to/unsafe name!.cfg") == "unsafe_name_.cfg"
    long_name = "a" * 200 + ".xml"
    sanitized = views._sanitize_filename(long_name)
    assert len(sanitized) <= 100 + len(".xml")
    assert sanitized != ""


def test_render_template_success():
    s = "Hello {{ name }}!"
    out = views.render_template(s, {"name": "world"})
    assert "Hello world!" in out


def test_render_template_syntax_error():
    s = "Hello {% if %} broken"
    with pytest.raises(TemplateSyntaxError):
        views.render_template(s, {})