import sys
import types
import pytest
from types import SimpleNamespace

import api.views as views


def test_get_template_from_mongo_success(monkeypatch):
    # Create a fake module api.utils.mongo with get_mongo_client
    fake_mod = types.ModuleType("api.utils.mongo")
    class FakeCollection:
        def find_one(self, q):
            return {"model": q.get("model"), "extension": q.get("extension"), "template": "TEMPLATE"}
    class FakeDB:
        device_templates = FakeCollection()
    def fake_get_client():
        return FakeDB()
    fake_mod.get_mongo_client = fake_get_client
    sys.modules["api.utils.mongo"] = fake_mod

    doc = views.get_template_from_mongo("X", "xml")
    assert isinstance(doc, dict)
    assert doc["template"] == "TEMPLATE"

    # cleanup
    del sys.modules["api.utils.mongo"]


def test_get_template_from_mongo_handles_exception(monkeypatch):
    fake_mod = types.ModuleType("api.utils.mongo")
    def bad_get():
        raise RuntimeError("nope")
    fake_mod.get_mongo_client = bad_get
    import sys
    sys.modules["api.utils.mongo"] = fake_mod

    doc = views.get_template_from_mongo("X", "xml")
    assert doc is None
    del sys.modules["api.utils.mongo"]