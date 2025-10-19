import os

import pytest
from django.test import RequestFactory

# Import dentro das funções para reduzir efeitos colaterais na importação do módulo
@pytest.fixture
def rf():
    return RequestFactory()


def test_require_api_key_not_configured(monkeypatch, rf):
    """
    Se a variável de ambiente PROVISION_API_KEY não estiver configurada,
    _require_api_key deve retornar None (não exige API key).
    """
    monkeypatch.delenv("PROVISION_API_KEY", raising=False)
    from api import views

    request = rf.get("/download-xml/")
    result = views._require_api_key(request)
    assert result is None


def test_require_api_key_matches(monkeypatch, rf):
    """
    Quando PROVISION_API_KEY está configurada e o header X-API-KEY bate,
    _require_api_key deve retornar None (autenticado).
    """
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    from api import views

    request = rf.get("/download-xml/")
    # header normalmente chega em META como HTTP_X_API_KEY
    request.META["HTTP_X_API_KEY"] = "secret-key"
    result = views._require_api_key(request)
    assert result is None


def test_require_api_key_mismatch_returns_403(monkeypatch, rf):
    """
    Quando PROVISION_API_KEY está configurada e o header X-API-KEY está incorreto,
    _require_api_key deve retornar uma HttpResponseForbidden (status 403).
    """
    monkeypatch.setenv("PROVISION_API_KEY", "secret-key")
    from api import views

    request = rf.get("/download-xml/")
    request.META["HTTP_X_API_KEY"] = "wrong-key"
    resp = views._require_api_key(request)
    # A função retorna HttpResponseForbidden em caso de chave inválida
    assert resp is not None
    # Confirma que é 403
    assert getattr(resp, "status_code", None) == 403