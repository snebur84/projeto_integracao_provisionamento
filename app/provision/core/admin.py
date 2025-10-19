from django.contrib import admin
from .models import DeviceProfile, DeviceConfig, Provisioning


class DeviceInline(admin.TabularInline):
    model = DeviceConfig
    extra = 1
    fields = ("identifier", "mac_address", "display_name", "user_register", "passwd_register", "attempts_provisioning")
    readonly_fields = ("attempts_provisioning",)
    show_change_link = True


@admin.register(DeviceProfile)
class DeviceProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "sip_server", "port_server", "protocol_type", "srtp_enable", "created_at")
    search_fields = ("name", "sip_server", "template_ref")
    inlines = [DeviceInline]
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("protocol_type", "srtp_enable")


@admin.register(DeviceConfig)
class DeviceConfigAdmin(admin.ModelAdmin):
    list_display = ("identifier", "mac_address", "display_name", "profile", "attempts_provisioning", "provisioned_at")
    search_fields = ("identifier", "mac_address", "display_name")
    list_filter = ("profile", "exported_to_rps")
    readonly_fields = ("created_at", "updated_at", "attempts_provisioning")
    fieldsets = (
        (None, {"fields": ("profile", "identifier", "mac_address", "display_name", "user_register", "passwd_register")}),
        ("State", {"fields": ("ip_address", "public_ip", "private_ip", "provisioned_at", "attempts_provisioning", "exported_to_rps")}),
        ("Metadata", {"fields": ("metadata",)}),
    )


@admin.register(Provisioning)
class ProvisioningAdmin(admin.ModelAdmin):
    list_display = ("mac_address", "identifier", "status", "vendor", "model", "version", "created_at")
    search_fields = ("mac_address", "identifier", "vendor", "model", "notes")
    list_filter = ("status", "vendor", "model")
    readonly_fields = ("device", "mac_address", "identifier", "vendor", "model", "version", "public_ip", "private_ip", "filename", "template_ref", "user_agent", "notes", "created_at", "updated_at")