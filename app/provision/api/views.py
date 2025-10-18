from django.http import HttpResponse, HttpResponseForbidden
from drf_spectacular.utils import extend_schema
from django.views.decorators.http import require_GET
import logging
import os
import re

logger = logging.getLogger(__name__)

def parse_user_agent(request):
    """
    More tolerant UA parser:
    - requires at least 4 space-separated parts;
    - vendor=model parts[0], model=parts[1], version=parts[2], identifier=rest joined by space
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

def get_device_config(identifier):
    from core.models import DeviceConfig
    try:
        return DeviceConfig.objects.get(identifier=identifier)
    except DeviceConfig.DoesNotExist:
        return None

def get_template_from_mongo(model, ext):
    from .utils.mongo import get_mongo_client
    db = get_mongo_client()
    try:
        # ensure indexes/queries are explicit
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
    # remove path components
    basename = os.path.basename(name)
    # replace disallowed chars with underscore
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', basename)
    # limit length
    if len(safe) > 100:
        safe = safe[:100]
    if not safe:
        safe = "download"
    return safe

@extend_schema(
    methods=['GET'],
    description="Download do arquivo de configuração do dispositivo. User-Agent esperado: 'vendor model version identifier'",
    responses={
        200: None,
        403: None,
    },
)

@require_GET
def download_config(request, filename=None):
    # Optional API key enforcement (if environment provides PROVISION_API_KEY)
    api_key_env = os.environ.get('PROVISION_API_KEY')
    if api_key_env:
        provided = request.META.get('HTTP_X_API_KEY') or request.headers.get('X-API-KEY')
        if provided != api_key_env:
            logger.warning("Unauthorized request - missing/invalid API key from %s", request.META.get('REMOTE_ADDR'))
            return HttpResponseForbidden("Forbidden: invalid API key")

    ua_data = parse_user_agent(request)
    if not ua_data:
        return HttpResponseForbidden("Forbidden: Invalid User-Agent format")
    vendor, model, version, identifier = ua_data
    logger.info("Request for config: vendor=%s model=%s version=%s identifier=%s", vendor, model, version, identifier)

    device = get_device_config(identifier)
    if not device:
        logger.warning("Device identifier not found: %s", identifier)
        return HttpResponseForbidden("Forbidden: Identifier not found")

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

    # prepare context
    context = {
        "vendor": device.vendor,
        "model": device.model,
        "version": device.version,
        "identifier": device.identifier,
        "ip_address": getattr(device, "ip_address", ""),
        "location": getattr(device, "location", ""),
    }

    # render template safely and catch rendering errors
    try:
        config_content = render_template(template_doc["template"], context)
    except Exception:
        # render_template already logged specifics
        return HttpResponseForbidden("Forbidden: error rendering template")

    # sanitize filename before sending in header
    if filename:
        download_name = _sanitize_filename(filename)
    else:
        download_name = _sanitize_filename(f"{model}.{ext}")

    content_type = "application/xml" if ext == "xml" else "text/plain"
    response = HttpResponse(config_content, content_type=content_type)
    # header value is quoted to avoid header injection; filename sanitized above
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    logger.info("Served config for identifier=%s as %s", identifier, download_name)
    return response