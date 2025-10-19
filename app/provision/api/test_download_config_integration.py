import os
import pytest
from django.urls import reverse
from django.test import Client

import api.views as views
from core.models import DeviceProfile, DeviceConfig


@pytest.mark.django_db
def test_download_config_success(monkeypatch, settings):
    client = Client()
    # ensure OAuth path is not used in test: force OAuth2Authentication to None
    monkeypatch.setattr(views, "OAuth2Authentication", None)

    # create profile and device
    profile = DeviceProfile.objects.create(name="P1")
    device = DeviceConfig.objects.create(profile=profile, identifier="dev-123", mac_address="aabbcc112233")

    # mock get_template_from_mongo to return a simple template
    monkeypatch.setattr(views, "get_template_from_mongo", lambda model, ext: {"template": "cfg for {{ identifier }}", "model": model, "extension": ext})

    # set API key and perform request with matching header
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    ua = "Vendor Model ver dev-123"
    resp = client.get("/api/download-xml/", HTTP_USER_AGENT=ua, HTTP_X_API_KEY="secret-key")
    assert resp.status_code == 200
    assert b"cfg for dev-123" in resp.content


@pytest.mark.django_db
def test_download_config_forbidden_without_api_key(monkeypatch):
    client = Client()
    monkeypatch.setattr(views, "OAuth2Authentication", None)
    profile = DeviceProfile.objects.create(name="P2")
    DeviceConfig.objects.create(profile=profile, identifier="dev-456", mac_address="112233445566")
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    ua = "Vendor Model ver dev-456"
    # Do not send API key header -> should be 403
    resp = client.get("/api/download-xml/", HTTP_USER_AGENT=ua)
    assert resp.status_code == 403