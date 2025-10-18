from django.contrib import admin
import logging

logger = logging.getLogger(__name__)

# Register DeviceConfig in admin if available. Import lazily to avoid errors
try:
    from .models import DeviceConfig

    class DeviceConfigAdmin(admin.ModelAdmin):
        """
        Basic admin configuration. list_display is populated dynamically from the model's
        first few fields to avoid hardcoding field names (models may vary).
        """
        try:
            _fields = [f.name for f in DeviceConfig._meta.fields][:8]
            list_display = _fields
        except Exception:
            list_display = ('__str__',)

        search_fields = ('identifier', 'model', 'vendor',)
        list_per_page = 50

    admin.site.register(DeviceConfig, DeviceConfigAdmin)
except Exception as exc:
    # If the model is not present yet, log and skip registration.
    logger.debug("DeviceConfig admin registration skipped (model missing): %s", exc)