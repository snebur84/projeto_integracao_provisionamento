import pytest
import api.views as views


class DoesNotExist(Exception):
    pass


class FakeObjects:
    def __init__(self, by_mac=None, by_id=None):
        self.by_mac = by_mac
        self.by_id = by_id

    def get(self, **kwargs):
        if "mac_address" in kwargs:
            if self.by_mac is None:
                raise DoesNotExist()
            return self.by_mac
        if "identifier" in kwargs:
            if self.by_id is None:
                raise DoesNotExist()
            return self.by_id
        raise DoesNotExist()


class FakeDeviceConfig:
    objects = None


def test_get_device_config_by_mac(monkeypatch):
    d = SimpleNamespace = type("SN", (), {})  # placeholder type creation
    obj = object()
    FakeDeviceConfig.objects = FakeObjects(by_mac=obj, by_id=None)
    monkeypatch.setattr(views, "_get_models", lambda: (FakeDeviceConfig, None, None))
    res = views.get_device_config("AA:BB:CC:11:22:33")
    assert res is obj


def test_get_device_config_by_identifier(monkeypatch):
    obj = object()
    FakeDeviceConfig.objects = FakeObjects(by_mac=None, by_id=obj)
    monkeypatch.setattr(views, "_get_models", lambda: (FakeDeviceConfig, None, None))
    res = views.get_device_config("device-1")
    assert res is obj


def test_get_device_config_handles_missing(monkeypatch):
    FakeDeviceConfig.objects = FakeObjects(by_mac=None, by_id=None)
    monkeypatch.setattr(views, "_get_models", lambda: (FakeDeviceConfig, None, None))
    res = views.get_device_config("device-unknown")
    assert res is None