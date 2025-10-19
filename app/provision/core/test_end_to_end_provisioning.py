import os
import pytest
from django.test import Client
from core.models import DeviceProfile, DeviceConfig
import api.views as views

@pytest.mark.django_db
def test_full_provision_flow(monkeypatch):
    client = Client()
    # disable OAuth path
    monkeypatch.setattr(views, "OAuth2Authentication", None)
    monkeypatch.setenv("PROVISION_API_KEY", "accept-key")

    profile = DeviceProfile.objects.create(name="ACCP")
    DeviceConfig.objects.create(profile=profile, identifier="accept-1", mac_address="aa:bb:cc:01:02:03")

    # stub mongo template
    monkeypatch.setattr(views, "get_template_from_mongo", lambda model, ext: {"template": "ACCEPT {{ identifier }}", "model": model, "extension": ext})

    ua = "Acme Model 1.2 accept-1"
    resp = client.get("/api/download-xml/config.cfg", HTTP_USER_AGENT=ua, HTTP_X_API_KEY="accept-key")
    assert resp.status_code == 200
    assert b"ACCEPT accept-1" in resp.content
    # basic header checks (Content-Disposition may be present)
    cd = resp.get("Content-Disposition", "")
    assert "config.cfg" in cd or cd == ""  # allow either presence or not depending on view