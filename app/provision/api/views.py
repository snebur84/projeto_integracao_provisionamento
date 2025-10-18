from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.views.decorators.http import require_GET
import logging
import os
import re
import ipaddress
from drf_spectacular.utils import extend_schema
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

logger = logging.getLogger(__name__)


def _require_api_key(request):
    """
    Enforce optional API key if PROVISION_API_KEY is set in environment.
    Returns None if OK, or HttpResponseForbidden if invalid/missing.
    """
    api_key_env = os.environ.get('PROVISION_API_KEY')
    if not api_key_env:
        return None
    provided = request.META.get('HTTP_X_API_KEY') or request.headers.get('X-API-KEY')
    if provided != api_key_env:
        logger.warning("Unauthorized request - missing/invalid API key from %s", request.META.get('REMOTE_ADDR'))
        return HttpResponseForbidden("Forbidden: invalid API key")
    return None


def parse_user_agent(request):
    """
    More tolerant UA parser:
    - requires at least 4 space-separated parts;
    - vendor = parts[0], model = parts[1], version = parts[2], identifier = rest joined by space
    The identifier token in our flow is expected to be (or contain) the MAC address or an identifier.
    """
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
    """
    Normalize MAC-like input: strip, lowercase, remove non-hex characters.
    Returns normalized hex string, or empty string if nothing valid.
    """
    if not value:
        return ""
    v = value.strip().lower()
    # remove any non-hex characters (colons, dashes, dots, spaces)
    v = re.sub(r'[^0-9a-f]', '', v)
    return v


def _is_private_ip(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private
    except Exception:
        return False


def _extract_public_ip(request):
    """
    Determine the client's public IP by checking common headers (X-Forwarded-For)
    and REMOTE_ADDR fallback. Returns string or None.
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR') or request.headers.get('X-Forwarded-For')
    if xff:
        parts = [p.strip() for p in xff.split(',') if p.strip()]
        if parts:
            for p in parts:
                try:
                    ipaddress.ip_address(p)
                    # prefer first valid non-private IP as public
                    if not _is_private_ip(p):
                        return p
                except ValueError:
                    continue
            # if no public found, return first valid anyway
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
    """
    Try to obtain a private/local IP reported by the device.
    Approaches:
    - check explicit headers often used to convey device local IP (custom headers)
    - try to inspect X-Forwarded-For list and pick a private IP if present
    """
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
    """
    Lazy import of DeviceConfig model.
    Lookup behavior: prefer lookup by mac_address (normalized),
    falling back to identifier if mac lookup fails (keeps backward compatibility).
    Returns model instance or None.
    """
    try:
        from core.models import DeviceConfig
    except Exception as exc:
        logger.exception("core.models.DeviceConfig import failed: %s", exc)
        return None

    # try mac lookup first
    norm_mac = _normalize_mac(identifier)
    if norm_mac:
        try:
            return DeviceConfig.objects.get(mac_address=norm_mac)
        except DeviceConfig.DoesNotExist:
            # continue to fallback lookup by identifier field
            pass
        except Exception as exc:
            logger.exception("Error fetching DeviceConfig by mac_address=%s: %s", norm_mac, exc)
            return None

    # fallback to identifier field lookup (older behavior)
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
    """
    Normalize and sanitize filename to avoid header injection and path traversal.
    Allows only alphanumerics, dot, dash and underscore. Truncates if too long.
    """
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
        "A API tenta normalizar o token final como MAC (removendo ':' '-' etc.) e procura por mac_address no banco; "
        "caso não encontre, faz fallback por identifier.\n\n"
        "Comportamento de provisionamento:\n"
        "- attempts_provisioning é incrementado a cada tentativa (mantém total acumulado).\n"
        "- provisioned_at é atualizado quando o template é servido com sucesso (timestamp atual).\n\n"
        "ATENÇÃO: passwd_register será incluído no arquivo retornado e também é retornado pelo endpoint JSON."
    ),
    responses={
        200: None,
        403: None,
    },
)
@require_GET
def download_config(request, filename=None):
    """
    Endpoint: renders and returns the device configuration template.

    Adjustments implemented:
    - lookup prefers mac_address (normalized) from the identifier token;
    - increments attempts_provisioning on each request attempt (cumulative total);
    - on successful serve, sets provisioned_at to now (but DOES NOT reset attempts_provisioning);
    - collects public_ip/private_ip from request and persists them when changed;
    - passwd_register is included in the template context (available to the downloaded file).
    """
    # Optional API key enforcement
    key_check = _require_api_key(request)
    if key_check:
        return key_check

    ua_data = parse_user_agent(request)
    if not ua_data:
        return HttpResponseForbidden("Forbidden: Invalid User-Agent format")
    vendor, model, version, identifier = ua_data
    logger.info("Request for config: vendor=%s model=%s version=%s identifier=%s", vendor, model, version, identifier)

    device = get_device_config(identifier)
    if not device:
        logger.warning("Device not found for identifier/mac: %s", identifier)
        return HttpResponseForbidden("Forbidden: Device not found")

    # attempt to collect IPs from request (but don't overwrite unless changed)
    public_ip = _extract_public_ip(request)
    private_ip = _extract_private_ip(request)
    ip_update_fields = []
    try:
        if public_ip and getattr(device, "public_ip", None) != public_ip:
            device.public_ip = public_ip
            ip_update_fields.append("public_ip")
        if private_ip and getattr(device, "private_ip", None) != private_ip:
            device.private_ip = private_ip
            ip_update_fields.append("private_ip")
        # backward-compatible ip_address population
        if not getattr(device, "ip_address", None):
            if private_ip:
                device.ip_address = private_ip
                ip_update_fields.append("ip_address")
            elif public_ip:
                device.ip_address = public_ip
                ip_update_fields.append("ip_address")
    except Exception as exc:
        logger.exception("Failed to compute IP updates for device %s: %s", device, exc)

    # increment attempts_provisioning for this attempt (cumulative)
    try:
        current_attempts = int(getattr(device, "attempts_provisioning", 0) or 0)
        device.attempts_provisioning = current_attempts + 1
        if "attempts_provisioning" not in ip_update_fields:
            ip_update_fields.append("attempts_provisioning")
        if ip_update_fields:
            device.save(update_fields=ip_update_fields)
        else:
            # no other fields to update, but attempts_provisioning changed
            device.save(update_fields=["attempts_provisioning"])
    except Exception as exc:
        logger.exception("Failed to increment attempts_provisioning for device %s: %s", getattr(device, "identifier", None), exc)

    # determine extension: default xml, or cfg if filename endswith .cfg
    ext = "xml"
    if filename and filename.lower().endswith(".cfg"):
        ext = "cfg"

    template_doc = get_template_from_mongo(model, ext)
    if not template_doc:
        logger.warning("Configuration template not found for model=%s ext=%s", model, ext)
        return HttpResponseForbidden("Configuration template not found for this model and extension")

    if 'template' not in template_doc or not isinstance(template_doc['template'], str):
        logger.error("Invalid template document structure for model=%s ext=%s: %s", model, ext, template_doc)
        return HttpResponseForbidden("Configuration template invalid")

    # prepare context: include passwd_register explicitly as requested
    context = {
        "vendor": device.vendor,
        "model": device.model,
        "version": device.version,
        "identifier": device.identifier,
        "ip_address": getattr(device, "ip_address", ""),
        "private_ip": getattr(device, "private_ip", ""),
        "public_ip": getattr(device, "public_ip", ""),
        "location": getattr(device, "location", ""),
        # SIP fields (passwd_register intentionally included)
        "sip_server": getattr(device, "sip_server", ""),
        "port_server": getattr(device, "port_server", ""),
        "protocol_type": getattr(device, "protocol_type", ""),
        "mac_address": getattr(device, "mac_address", ""),
        "user_register": getattr(device, "user_register", ""),
        "passwd_register": getattr(device, "passwd_register", ""),
        "display_name": getattr(device, "display_name", ""),
        "display_number": getattr(device, "display_number", ""),
        "backup_server": getattr(device, "backup_server", ""),
        "domain_server": getattr(device, "domain_server", ""),
        "time_zone": getattr(device, "time_zone", ""),
        "srtp_enable": getattr(device, "srtp_enable", False),
        "created_at": getattr(device, "created_at", None),
        "updated_at": getattr(device, "updated_at", None),
        "provisioned_at": getattr(device, "provisioned_at", None),
        "attempts_provisioning": getattr(device, "attempts_provisioning", 0),
        "exported_to_rps": getattr(device, "exported_to_rps", False),
    }

    # render template safely and catch rendering errors
    try:
        config_content = render_template(template_doc["template"], context)
    except Exception:
        # render_template already logged specifics
        return HttpResponseForbidden("Forbidden: error rendering template")

    # On successful render/serve, set provisioned_at to now (DO NOT reset attempts_provisioning)
    try:
        device.provisioned_at = timezone.now()
        # keep attempts_provisioning cumulative (do not reset to 0)
        device.save(update_fields=["provisioned_at"])
        logger.info("Marked device %s provisioned at %s (attempts preserved)", getattr(device, "identifier", None), device.provisioned_at)
    except Exception as exc:
        logger.exception("Failed to mark provisioned_at for device %s: %s", getattr(device, "identifier", None), exc)

    # sanitize filename before sending in header
    if filename:
        download_name = _sanitize_filename(filename)
    else:
        download_name = _sanitize_filename(f"{model}.{ext}")

    content_type = "application/xml" if ext == "xml" else "text/plain"
    response = HttpResponse(config_content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    logger.info("Served config for device mac/identifier=%s as %s", getattr(device, "mac_address", None) or getattr(device, "identifier", None), download_name)
    return response


@extend_schema(
    methods=['GET'],
    description=(
        "Retorna os dados do dispositivo (JSON) buscados por mac_address ou identifier.\n\n"
        "Busca: o parâmetro identifier pode ser um MAC (com ou sem separadores); a API tentará normalizar "
        "e localizar pelo campo mac_address antes de tentar o campo identifier.\n\n"
        "ATENÇÃO: passwd_register está exposto neste endpoint conforme solicitado."
    ),
    responses={
        200: {
            "application/json": {
                "type": "object"
            }
        },
        404: None,
        403: None,
    },
)
@require_GET
def get_device_info(request, identifier=None):
    """
    Returns JSON representation of DeviceConfig by mac or identifier.
    If identifier is None, tries to parse it from User-Agent (same logic as download_config).
    Collects public/private IPs from request and persists them when changed.
    passwd_register is exposed in the JSON response.
    """
    # Optional API key enforcement
    key_check = _require_api_key(request)
    if key_check:
        return key_check

    if identifier is None:
        ua_data = parse_user_agent(request)
        if not ua_data:
            return HttpResponseForbidden("Forbidden: Invalid User-Agent format")
        identifier = ua_data[3]

    device = get_device_config(identifier)
    if not device:
        logger.debug("get_device_info: device not found for identifier=%s", identifier)
        raise Http404("Device not found")

    # attempt to collect IPs from the request and persist if changed
    public_ip = _extract_public_ip(request)
    private_ip = _extract_private_ip(request)
    update_fields = []
    try:
        if public_ip and getattr(device, "public_ip", None) != public_ip:
            device.public_ip = public_ip
            update_fields.append("public_ip")
        if private_ip and getattr(device, "private_ip", None) != private_ip:
            device.private_ip = private_ip
            update_fields.append("private_ip")
        if not getattr(device, "ip_address", None):
            if private_ip:
                device.ip_address = private_ip
                update_fields.append("ip_address")
            elif public_ip:
                device.ip_address = public_ip
                update_fields.append("ip_address")
        if update_fields:
            device.save(update_fields=update_fields)
            logger.info("get_device_info updated IPs for identifier=%s fields=%s", identifier, update_fields)
    except Exception as exc:
        logger.exception("get_device_info failed to persist IPs for %s: %s", identifier, exc)

    # Build a serializable dict from model fields.
    data = {
        "vendor": device.vendor,
        "model": device.model,
        "version": device.version,
        "identifier": device.identifier,
        "mac_address": getattr(device, "mac_address", None),
        "ip_address": getattr(device, "ip_address", None),
        "public_ip": getattr(device, "public_ip", None),
        "private_ip": getattr(device, "private_ip", None),
        "location": getattr(device, "location", None),
        "sip_server": getattr(device, "sip_server", None),
        "port_server": getattr(device, "port_server", None),
        "protocol_type": getattr(device, "protocol_type", None),
        # passwd_register is now exposed
        "passwd_register": getattr(device, "passwd_register", None),
        "user_register": getattr(device, "user_register", None),
        "display_name": getattr(device, "display_name", None),
        "display_number": getattr(device, "display_number", None),
        "backup_server": getattr(device, "backup_server", None),
        "domain_server": getattr(device, "domain_server", None),
        "time_zone": getattr(device, "time_zone", None),
        "srtp_enable": bool(getattr(device, "srtp_enable", False)),
        "created_at": device.created_at.isoformat() if getattr(device, "created_at", None) else None,
        "updated_at": device.updated_at.isoformat() if getattr(device, "updated_at", None) else None,
        "provisioned_at": device.provisioned_at.isoformat() if getattr(device, "provisioned_at", None) else None,
        "attempts_provisioning": int(getattr(device, "attempts_provisioning", 0)),
        "exported_to_rps": bool(getattr(device, "exported_to_rps", False)),
    }

    # Use DjangoJSONEncoder to handle datetimes if any slipped through
    return JsonResponse(data, encoder=DjangoJSONEncoder, safe=True)