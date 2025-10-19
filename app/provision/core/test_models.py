import pytest
from django.core.exceptions import ValidationError
from core.models import DeviceProfile, DeviceConfig


@pytest.mark.django_db
def test_deviceprofile_port_validation():
    p = DeviceProfile(name="TP", port_server=5060)
    # valid
    p.full_clean()  # should not raise

    p.port_server = 80
    with pytest.raises(ValidationError):
        p.full_clean()


@pytest.mark.django_db
def test_deviceprofile_str_and_metadata_default():
    p = DeviceProfile.objects.create(name="PSTR")
    assert str(p) == "PSTR"
    assert isinstance(p.metadata, dict)


@pytest.mark.django_db
def test_deviceconfig_str_returns_identifier_or_mac():
    p = DeviceProfile.objects.create(name="PX")
    d = DeviceConfig.objects.create(profile=p, identifier="id-1", mac_address="aa11")
    assert str(d) == "id-1"
    d.identifier = ""
    d.save()
    assert str(d) == "aa11"