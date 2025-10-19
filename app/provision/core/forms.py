from django import forms
from django.forms import inlineformset_factory
from .models import DeviceProfile, DeviceConfig


class DeviceProfileForm(forms.ModelForm):
    class Meta:
        model = DeviceProfile
        fields = ["name", "sip_server", "port_server", "protocol_type", "backup_server", "domain_server", "time_zone", "srtp_enable", "template_ref", "metadata"]
        widgets = {
            "metadata": forms.Textarea(attrs={"rows": 3}),
            "template_ref": forms.TextInput(attrs={"placeholder": "Mongo template _id or identifier"}),
        }


class DeviceConfigForm(forms.ModelForm):
    class Meta:
        model = DeviceConfig
        fields = ["identifier", "mac_address", "display_name", "user_register", "passwd_register", "ip_address", "public_ip", "private_ip"]
        widgets = {
            "passwd_register": forms.PasswordInput(render_value=True),
        }


DeviceFormSet = inlineformset_factory(
    DeviceProfile,
    DeviceConfig,
    form=DeviceConfigForm,
    fields=["identifier", "mac_address", "display_name", "user_register", "passwd_register", "ip_address", "public_ip", "private_ip"],
    extra=1,
    can_delete=True,
)