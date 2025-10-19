from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.views.decorators.http import require_GET
import logging
import os
import re
import ipaddress
from drf_spectacular.utils import extend_schema
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from api.utils.mongo import get_mongo_client

# OAuth2 auth helper (django-oauth-toolkit)
try:
    from oauth2_provider.contrib.rest_framework import OAuth2Authentication
except Exception:
    OAuth2Authentication = None

logger = logging.getLogger(__name__)

# Lazy import helpers to avoid circular import at module import time
def _get_models():
    try:
        from core.models import DeviceConfig, Provisioning, DeviceProfile
        return DeviceConfig, Provisioning, DeviceProfile
    except Exception as exc:
        logger.exception("core.models import failed: %s", exc)
        return None, None, None


def _require_api_key(request):
    api_key_env = os.environ.get('PROVISION_API_KEY')
    if not api_key_env:
        return None
    provided = request.META.get('HTTP_X_API_KEY') or request.headers.get('X-API-KEY')
    if provided != api_key_env:
        logger.warning("Unauthorized request - missing/invalid API key from %s", request.META.get('REMOTE_ADDR'))
        return HttpResponseForbidden("Forbidden: invalid API key")
    return None


def parse_user_agent(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').strip()
    parts = user_agent.split()
    if len(parts) < 4:
        logger.debug("User-Agent parsing failed: expected >=4 parts, got %s (UA=%s)", len(parts), user_agent)
        return None
    vendor = parts[0]
    model = parts[1]
    version = parts[2]
    identifier = " ".join(parts[3:])
    return vendor, model, version, identifier


def _normalize_mac(value: str):
    if not value:
        return ""
    v = value.strip().lower()
    v = re.sub(r'[^0-9a-f]', '', v)
    return v


def _is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except Exception:
        return False


def _extract_public_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR') or request.headers.get('X-Forwarded-For')
    if xff:
        parts = [p.strip() for p in xff.split(',') if p.strip()]
        if parts:
            for p in parts:
                try:
                    ipaddress.ip_address(p)
                    if not _is_private_ip(p):
                        return p
                except ValueError:
                    continue
            for p in parts:
                try:
                    ipaddress.ip_address(p)
                    return p
                except ValueError:
                    continue
    remote = request.META.get('REMOTE_ADDR')
    try:
        if remote:
            ipaddress.ip_address(remote)
            return remote
    except ValueError:
        return None
    return None


def _extract_private_ip(request):
    candidates = [
        request.META.get('HTTP_X_PRIVATE_IP'),
        request.META.get('HTTP_X_DEVICE_PRIVATE_IP'),
        request.META.get('HTTP_X_LOCAL_IP'),
        request.META.get('HTTP_X_CLIENT_IP'),
        request.headers.get('X-Private-IP') if hasattr(request, 'headers') else None,
        request.headers.get('X-Device-Private-IP') if hasattr(request, 'headers') else None,
    ]
    for c in candidates:
        if c:
            c = c.strip()
            for maybe in [p.strip() for p in c.split(',') if p.strip()]:
                if _is_private_ip(maybe):
                    return maybe
    xff = request.META.get('HTTP_X_FORWARDED_FOR') or request.headers.get('X-Forwarded-For')
    if xff:
        for p in [pp.strip() for pp in xff.split(',') if pp.strip()]:
            if _is_private_ip(p):
                return p
    return None


def get_device_config(identifier):
    DeviceConfig, Provisioning, DeviceProfile = _get_models()
    if not DeviceConfig:
        return None
    norm_mac = _normalize_mac(identifier)
    if norm_mac:
        try:
            return DeviceConfig.objects.get(mac_address=norm_mac)
        except DeviceConfig.DoesNotExist:
            pass
        except Exception as exc:
            logger.exception("Error fetching DeviceConfig by mac_address=%s: %s", norm_mac, exc)
            return None
    try:
        return DeviceConfig.objects.get(identifier=identifier)
    except DeviceConfig.DoesNotExist:
        return None
    except Exception as exc:
        logger.exception("Error fetching DeviceConfig by identifier=%s: %s", identifier, exc)
        return None


def get_template_from_mongo(model: str, ext: str):
    """
    Busca template no MongoDB a partir do campo 'model' (case-insensitive) e 'extension'.
    Tentativas (em ordem):
      1) buscar por documento com campo 'model' case-insensitive igual a model e extension == ext
      2) buscar por _id igual a model.lower() (compatibilidade com chaves salvas em lower-case)
      3) fallback: buscar qualquer template com extension == ext
    Retorna o documento (dict) ou None.
    """
    try:
        db = get_mongo_client()
    except Exception as exc:
        logger.exception("Failed to get mongo DB handle: %s", exc)
        return None

    try:
        coll = getattr(db, "device_templates", db.get_collection("device_templates"))
        model_q = (model or "").strip().lower()
        # 1) buscar por campo 'model' case-insensitive
        if model_q:
            # escapamos para evitar metacaracteres regex
            regex = f"^{re.escape(model_q)}$"
            doc = coll.find_one({"model": {"$regex": regex, "$options": "i"}, "extension": ext})
            if doc:
                return doc

            # 2) buscar por _id igual ao model em lower-case
            doc = coll.find_one({"_id": model_q})
            if doc:
                return doc

        # 3) fallback por extensão
        doc = coll.find_one({"extension": ext})
        if doc:
            return doc

        return None
    except Exception as exc:
        logger.exception("MongoDB query failed for model=%s ext=%s: %s", model, ext, exc)
        return None

def substitute_percent_placeholders(template_text: str, context: dict) -> str:
    """
    Substitui placeholders no formato %%nome%% por valores vindos de context.
    - Faz lookup case-insensitive da chave no context (usa chave lower()).
    - Booleanos são convertidos em '1' / '0' (útil para flags como %%vlanactive%%).
    - Valores None ou keys ausentes são substituídos por string vazia.
    """
    if not template_text:
        return template_text

    # preparar um dicionário com chaves lower-case para lookup rápido
    ctx = {str(k).lower(): v for k, v in (context or {}).items()}

    def repl(match: re.Match) -> str:
        key = (match.group(1) or "").strip().lower()
        val = ctx.get(key, "")
        # converter booleanos para 1/0
        if isinstance(val, bool):
            return "1" if val else "0"
        # None -> empty
        if val is None:
            return ""
        # se for lista/dict, converter para string JSON/simple
        if isinstance(val, (list, dict)):
            try:
                import json
                return json.dumps(val, ensure_ascii=False)
            except Exception:
                return str(val)
        return str(val)

    # regex procura %%nome%% — nome composto por letras, dígitos e underscore
    pattern = re.compile(r"%%([A-Za-z0-9_]+)%%")
    return pattern.sub(repl, template_text)

def render_template(template_str, context):
    from django.template import Template, Context, TemplateSyntaxError
    try:
        django_template = Template(template_str)
        return django_template.render(Context(context))
    except TemplateSyntaxError as exc:
        logger.exception("Template syntax error while rendering: %s", exc)
        raise


def _sanitize_filename(name):
    if not name:
        return name
    basename = os.path.basename(name)
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', basename)
    if len(safe) > 100:
        safe = safe[:100]
    if not safe:
        safe = "download"
    return safe


@extend_schema(
    methods=['GET'],
    description=(
        "Download do arquivo de configuração do dispositivo.\n\n"
        "User-Agent esperado: 'vendor model version <mac|identifier>' (identifier pode conter separadores). "
    ),
    responses={200: None, 403: None},
)
@require_GET
def download_config(request, filename: str = None):
    """
    Endpoint de download de configuração (ajustado para usar modelo extraído do User-Agent).

    - Extrai vendor, model, version, identifier (MAC ou account) do User-Agent via parse_user_agent().
      Exemplo de UA: "Ale H2P 2.10 3c28a60357a0" -> vendor='Ale', model='H2P', version='2.10', identifier='3c28a60357a0'
    - Normaliza model para lower() e usa get_template_from_mongo(model_lower, ext).
    - Normaliza mac (identifier) com _normalize_mac e busca DeviceConfig via get_device_config(identifier).
    - Prefere profile.template_ref quando presente (tentando versão original e lower-case).
    - Renderiza o template (campo 'template' do documento Mongo) com contexto combinado (device + profile + UA).
    - Retorna o conteúdo renderizado como application/xml (ext == 'xml') ou text/plain (cfg).
    """
    # parse User-Agent
    ua_data = parse_user_agent(request)
    if not ua_data:
        logger.warning("Invalid User-Agent format for request from %s", request.META.get("REMOTE_ADDR"))
        return HttpResponseForbidden("Forbidden: Invalid User-Agent format")

    vendor, model, version, identifier = ua_data
    model_for_query = (model or "").strip().lower()
    # identifier normalmente é mac ou account; normalizar para busca
    norm_identifier = _normalize_mac(identifier) or (identifier or "").strip()

    # localizar device (tenta MAC normalizado primeiro, depois identifier)
    device = None
    try:
        device = get_device_config(identifier)
    except Exception:
        logger.exception("Error fetching device for identifier=%s", identifier)
        device = None

    # inferir extensão (xml por padrão; se filename terminar com .cfg então cfg)
    ext = "xml"
    if filename and filename.lower().endswith(".cfg"):
        ext = "cfg"
    else:
        # também tentar inspecionar request.path ou outros parâmetros se necessário
        pass

    template_doc = None

    # 1) preferir profile.template_ref se device.profile estiver presente
    if device and device.profile and device.profile.template_ref:
        try:
            db = get_mongo_client()
            coll = getattr(db, "device_templates", db.get_collection("device_templates"))
            # tenta pelo template_ref exato
            tref = device.profile.template_ref
            template_doc = coll.find_one({"_id": tref})
            if not template_doc:
                # tenta versão lower-case (compatibilidade)
                t_lower = str(tref).strip().lower()
                if t_lower:
                    template_doc = coll.find_one({"_id": t_lower})
        except Exception:
            logger.exception("Mongo lookup by template_ref failed for %s", device.profile.template_ref)
            template_doc = None

    # 2) se não encontrou via template_ref, buscar por model extraído do UA
    if not template_doc:
        template_doc = get_template_from_mongo(model_for_query, ext)

    # 3) se ainda não encontrou -> reprovar
    if not template_doc:
        logger.warning("Configuration template not found for model=%s ext=%s", model_for_query, ext)
        return HttpResponseForbidden("Configuration template not found for this model and extension")

    # obter string do template com fallback (template -> content)
    template_str = template_doc.get("template") or template_doc.get("content")
    if not isinstance(template_str, str):
        logger.error("Invalid template document structure for model=%s ext=%s: %s", model_for_query, ext, template_doc)
        return HttpResponseForbidden("Configuration template invalid")

    # montar contexto para renderização (mapear placeholders)
    profile = device.profile if device else None

    context = {
        # UA / device-level
        "vendor": vendor,
        "model": model,
        "version": version,
        "identifier": device.identifier if device else (identifier or ""),
        "account": device.identifier if device else (identifier or ""),
        "displayname": device.display_name if device else "",
        "user": device.user_register if device else "",
        "passwd": device.passwd_register if device else "",
        "macaddress": device.mac_address if device and device.mac_address else norm_identifier,

        # IPs
        "ip_address": device.ip_address if device and device.ip_address else "",
        "public_ip": device.public_ip if device and device.public_ip else "",
        "private_ip": device.private_ip if device and device.private_ip else "",

        # profile-level placeholders
        "sipserver": profile.sip_server if profile else "",
        "port": profile.port_server if profile else "",
        "backsipserver": getattr(profile, "backup_server", "") if profile else "",
        "backsipport": getattr(profile, "backup_port", "") if profile else "",
        "proxy": getattr(profile, "proxy", "") if profile else "",
        "domain": profile.domain_server if profile else "",
        "registerttl": getattr(profile, "register_ttl", "") if profile else "",
        "codecs": getattr(profile, "voice_codecs", "") if profile else "",
        "ntpserver": getattr(profile, "ntp_server", "") if profile else "",
        "provisionserver": getattr(profile, "provision_server", "") if profile else "",
        "provisionfile": getattr(profile, "provision_file", "") if profile else "",
        "vlanactive": getattr(profile, "vlan_active", False) if profile else False,
        "vlanid": getattr(profile, "vlan_id", "") if profile else "",
    }

    # render template using existing helper (raises TemplateSyntaxError on bad template)
    try:
        config_content = render_template(template_str, context)
    except Exception:
        logger.exception("Error rendering template for device %s", getattr(device, "identifier", None))
        return HttpResponseForbidden("Forbidden: error rendering template")

    # aplicar substituição para placeholders do tipo %%nome%% usando os dados do context
    try:
        final_content = substitute_percent_placeholders(config_content, context)
    except Exception:
        logger.exception("Failed to substitute %%...%% placeholders for device %s", getattr(device, "identifier", None))
        final_content = config_content

    # devolver final_content em vez de config_content
    content_type = "application/xml; charset=utf-8" if ext == "xml" else "text/plain; charset=utf-8"
    return HttpResponse(final_content, content_type=content_type)

    # mark device provisioned (best-effort; preserve existing provisioning workflow)
    try:
        if device:
            device.provisioned_at = timezone.now()
            device.save(update_fields=["provisioned_at"])
    except Exception:
        logger.exception("Failed to update device provisioned_at for %s", getattr(device, "identifier", None))

    # return rendered configuration
    content_type = "application/xml; charset=utf-8" if ext == "xml" else "text/plain; charset=utf-8"
    return HttpResponse(config_content, content_type=content_type)