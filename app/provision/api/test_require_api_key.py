import os
import pytest
from django.test import RequestFactory
import api.views as views


@pytest.fixture
def rf():
    return RequestFactory()


def test_require_api_key_not_configured(monkeypatch, rf):
    monkeypatch.delenv("PROVISION_API_KEY", raising=False)
    req = rf.get("/download-xml/")
    assert views._require_api_key(req) is None


def test_require_api_key_matches(monkeypatch, rf):
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    req = rf.get("/download-xml/")
    req.META["HTTP_X_API_KEY"] = "secret-key"
    assert views._require_api_key(req) is None


def test_require_api_key_mismatch_returns_403(monkeypatch, rf):
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    req = rf.get("/download-xml/")
    req.META["HTTP_X_API_KEY"] = "wrong-key"
    resp = views._require_api_key(req)
    assert resp is not None
    assert getattr(resp, "status_code", None) == 403