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


def get_template_from_mongo(model, ext):
    from .utils.mongo import get_mongo_client
    db = get_mongo_client()
    try:
        return db.device_templates.find_one({"model": model, "extension": ext})
    except Exception as exc:
        logger.exception("MongoDB query failed for model=%s ext=%s: %s", model, ext, exc)
        return None


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
def download_config(request, filename=None):
    """
    Endpoint principal para download de configuração.
    Autenticação:
      - Primeiro tenta autenticar via OAuth2 Bearer token (django-oauth-toolkit). Requer escopo 'provision' ou 'read'.
      - Se não houver token ou escopo insuficiente, faz fallback para PROVISION_API_KEY (se configurada).
    """
    DeviceConfig, Provisioning, DeviceProfile = _get_models()

    # 1) Tentar autenticar via OAuth2 (se disponível)
    oauth_user = None
    oauth_token = None
    if OAuth2Authentication is not None:
        try:
            auth = OAuth2Authentication()
            auth_result = auth.authenticate(request)
            if auth_result:
                oauth_user, oauth_token = auth_result  # (user, token)
                # token.scope é uma string com scopes separados por espaços (AccessToken model)
                token_scopes = set(getattr(oauth_token, "scope", "").split())
                if not ({"provision", "read"} & token_scopes):
                    # scope insuficiente - ignore OAuth auth and fallback to API key
                    logger.warning("OAuth2 token present but missing required scope (need 'provision' or 'read')")
                    oauth_user = None
                    oauth_token = None
        except Exception as exc:
            logger.exception("OAuth2 authentication attempt failed: %s", exc)
            oauth_user = None
            oauth_token = None

    # 2) Se não autenticado por OAuth, verificar API key (fallback)
    if oauth_user is None:
        key_check = _require_api_key(request)
        if key_check:
            # registro de tentativa forbidden (sem device)
            try:
                Provisioning.objects.create(
                    mac_address="",
                    identifier="",
                    status=Provisioning.STATUS_FORBIDDEN,
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
                    notes="API key missing or invalid"
                )
            except Exception:
                logger.exception("Failed to record forbidden provisioning attempt (no API key).")
            return key_check

    # 3) a partir daqui: autenticação permitida (via OAuth ou API key)
    ua_data = parse_user_agent(request)
    if not ua_data:
        try:
            Provisioning.objects.create(
                mac_address="",
                identifier="",
                status=Provisioning.STATUS_FORBIDDEN,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
                notes="Invalid User-Agent format",
            )
        except Exception:
            logger.exception("Failed to record invalid UA provisioning attempt.")
        return HttpResponseForbidden("Forbidden: Invalid User-Agent format")
    vendor, model, version, identifier = ua_data
    logger.info("Request for config: vendor=%s model=%s version=%s identifier=%s", vendor, model, version, identifier)

    device = get_device_config(identifier)
    public_ip = _extract_public_ip(request)
    private_ip = _extract_private_ip(request)

    if not device:
        try:
            Provisioning.objects.create(
                mac_address=_normalize_mac(identifier),
                identifier=identifier,
                vendor=vendor,
                model=model,
                version=version,
                public_ip=public_ip,
                private_ip=private_ip,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
                status=Provisioning.STATUS_FORBIDDEN,
                notes="Device not found",
            )
        except Exception:
            logger.exception("Failed to record provisioning attempt for unknown device.")
        logger.warning("Device not found for identifier/mac: %s", identifier)
        return HttpResponseForbidden("Forbidden: Device not found")

    # update device ip fields if changed (but do not save attempts here)
    try:
        updated = False
        if public_ip and device.public_ip != public_ip:
            device.public_ip = public_ip
            updated = True
        if private_ip and device.private_ip != private_ip:
            device.private_ip = private_ip
            updated = True
        if not device.ip_address:
            if private_ip:
                device.ip_address = private_ip
                updated = True
            elif public_ip:
                device.ip_address = public_ip
                updated = True
        if updated:
            device.save(update_fields=[f for f in ("public_ip", "private_ip", "ip_address") if getattr(device, f, None) is not None])
    except Exception:
        logger.exception("Failed to compute/save IP updates for device %s", getattr(device, "identifier", None))

    # increment attempts_provisioning atomically and record Provisioning
    prov = None
    try:
        with transaction.atomic():
            DeviceConfig.objects.filter(pk=device.pk).update(attempts_provisioning=F('attempts_provisioning') + 1)
            device.refresh_from_db(fields=["attempts_provisioning"])
            prov = Provisioning.objects.create(
                device=device,
                mac_address=device.mac_address[:32] if device.mac_address else "",
                identifier=device.identifier[:255] if device.identifier else "",
                vendor=vendor,
                model=model,
                version=version,
                public_ip=public_ip,
                private_ip=private_ip,
                filename=(filename or ""),
                template_ref=(device.profile.template_ref if device.profile else ""),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
                status=Provisioning.STATUS_OK,
            )
    except Exception:
        logger.exception("Failed to create provisioning record for device %s", getattr(device, "identifier", None))

    # determine extension and try to fetch template
    ext = "xml"
    if filename and filename.lower().endswith(".cfg"):
        ext = "cfg"

    template_doc = None
    # prefer profile.template_ref if present
    if device.profile and device.profile.template_ref:
        try:
            from .utils.mongo import get_mongo_client
            db = get_mongo_client()
            # try by _id first
            template_doc = db.device_templates.find_one({"_id": device.profile.template_ref})
        except Exception:
            logger.exception("Mongo lookup by template_ref failed for %s", device.profile.template_ref)
    if not template_doc:
        template_doc = get_template_from_mongo(model, ext)

    if not template_doc:
        logger.warning("Configuration template not found for model=%s ext=%s", model, ext)
        try:
            if prov:
                prov.status = Provisioning.STATUS_FORBIDDEN
                prov.notes = "Template not found"
                prov.save(update_fields=["status", "notes"])
        except Exception:
            logger.exception("Failed to update provisioning record status after missing template.")
        return HttpResponseForbidden("Configuration template not found for this model and extension")

    if 'template' not in template_doc or not isinstance(template_doc['template'], str):
        logger.error("Invalid template document structure for model=%s ext=%s: %s", model, ext, template_doc)
        try:
            if prov:
                prov.status = Provisioning.STATUS_ERROR
                prov.notes = "Invalid template document"
                prov.save(update_fields=["status", "notes"])
        except Exception:
            logger.exception("Failed to update provisioning record after invalid template structure.")
        return HttpResponseForbidden("Configuration template invalid")

    # prepare context (profile defaults if present)
    context = {
        "vendor": device.profile.metadata.get("vendor") if device.profile and device.profile.metadata.get("vendor") else vendor,
        "model": model,
        "version": version,
        "identifier": device.identifier,
        "ip_address": device.ip_address or "",
        "private_ip": device.private_ip or "",
        "public_ip": device.public_ip or "",
        "location": getattr(device, "location", "") if hasattr(device, "location") else "",
        "sip_server": device.profile.sip_server if device.profile else "",
        "port_server": device.profile.port_server if device.profile else 5060,
        "protocol_type": device.profile.protocol_type if device.profile else DeviceProfile.PROTOCOL_UDP,
        "mac_address": device.mac_address,
        "user_register": device.user_register,
        "passwd_register": device.passwd_register,
        "display_name": device.display_name,
        "backup_server": device.profile.backup_server if device.profile else "",
        "domain_server": device.profile.domain_server if device.profile else "",
        "time_zone": device.profile.time_zone if device.profile else "",
        "srtp_enable": device.profile.srtp_enable if device.profile else False,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
        "provisioned_at": device.provisioned_at,
        "attempts_provisioning": device.attempts_provisioning,
        "exported_to_rps": device.exported_to_rps,
    }

    # Render template and handle errors
    try:
        config_content = render_template(template_doc["template"], context)
    except Exception:
        logger.exception("Error rendering template for device %s", getattr(device, "identifier", None))
        try:
            if prov:
                prov.status = Provisioning.STATUS_ERROR
                prov.notes = "Template render error"
                prov.save(update_fields=["status", "notes"])
        except Exception:
            pass
        return HttpResponseForbidden("Forbidden: error rendering template")

    # mark provisioned_at and update provisioning status
    try:
        device.provisioned_at = timezone.now()
        device.save(update_fields=["provisioned_at"])
        if prov:
            prov.status = Provisioning.STATUS_OK
            prov.save(update_fields=["status"])
        logger.info("Marked device %s provisioned at %s (attempts preserved)", getattr(device, "identifier", None), device.provisioned_at)
    except Exception:
        logger.exception("Failed to mark provisioned_at for device %s", getattr(device, "identifier", None))

    # sanitize filename and return response
    if filename:
        download_name = _sanitize_filename(filename)
    else:
        download_name = _sanitize_filename(f"{model}.{ext}")

    content_type = "application/xml" if ext == "xml" else "text/plain"
    response = HttpResponse(config_content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    logger.info("Served config for device mac/identifier=%s as %s", getattr(device, "mac_address", None) or getattr(device, "identifier", None), download_name)
    return response