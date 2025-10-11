from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_GET

def parse_user_agent(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').strip()
    parts = user_agent.split(" ")
    if len(parts) != 4:
        return None
    vendor, model, version, identifier = parts
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
    return db.device_templates.find_one({"model": model, "extension": ext})

def render_template(template_str, context):
    from django.template import Template, Context
    django_template = Template(template_str)
    return django_template.render(Context(context))

@require_GET
def download_config(request, filename=None):
    ua_data = parse_user_agent(request)
    if not ua_data:
        return HttpResponseForbidden("Forbidden: Invalid User-Agent format")
    vendor, model, version, identifier = ua_data

    device = get_device_config(identifier)
    if not device:
        return HttpResponseForbidden("Forbidden: Identifier not found")

    ext = "xml"
    if filename and filename.lower().endswith(".cfg"):
        ext = "cfg"
    template_doc = get_template_from_mongo(model, ext)
    if not template_doc:
        return HttpResponseForbidden("Configuration template not found for this model and extension")

    config_content = render_template(template_doc["template"], {
        "vendor": device.vendor,
        "model": device.model,
        "version": device.version,
        "identifier": device.identifier,
        "ip_address": device.ip_address,
        "location": device.location,
    })

    download_name = filename if filename else f"{model}.{ext}"
    content_type = "application/xml" if ext == "xml" else "text/plain"
    response = HttpResponse(config_content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    return response