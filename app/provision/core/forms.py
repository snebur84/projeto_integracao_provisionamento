from django import forms
from django.forms import inlineformset_factory
from .models import DeviceProfile, DeviceConfig


class DeviceProfileForm(forms.ModelForm):
    """
    Form para DeviceProfile com os campos adicionais usados pelos templates:
      - voice_codecs (%%codecs%%)
      - ntp_server (%%ntpserver%%)
      - provision_server / provision_file (%%provisionserver%% / %%provisionfile%%)
      - proxy (%%proxy%%)
      - register_ttl (%%registerttl%%)
      - vlan_active / vlan_id (%%vlanactive%% / %%vlanid%%)
      - backup_port (%%backsipport%%)
    """
    class Meta:
        model = DeviceProfile
        fields = [
            "name",
            "sip_server",
            "port_server",
            "protocol_type",
            "backup_server",
            "backup_port",
            "proxy",
            "domain_server",
            "time_zone",
            "register_ttl",
            "ntp_server",
            "voice_codecs",
            "provision_server",
            "provision_file",
            "vlan_active",
            "vlan_id",
            "srtp_enable",
            "template_ref",
            "metadata",
        ]
        widgets = {
            "metadata": forms.Textarea(attrs={"rows": 3}),
            "template_ref": forms.TextInput(attrs={"placeholder": "Mongo template _id or identifier"}),
            "voice_codecs": forms.TextInput(attrs={"placeholder": "e.g. PCMU,PCMA,G729"}),
        }
        help_texts = {
            "voice_codecs": "Lista separada por vírgula para preencher %%codecs%% no template.",
            "ntp_server": "Servidor NTP para preencher %%ntpserver%%.",
            "provision_server": "Endereço do servidor de provisionamento (%%provisionserver%%).",
            "provision_file": "Nome do arquivo de provisionamento (%%provisionfile%%).",
            "register_ttl": "Tempo em segundos para Register (%%registerttl%%).",
            "proxy": "Endereço do proxy (%%proxy%%).",
            "vlan_active": "Habilitar VLAN (%%vlanactive%%).",
            "vlan_id": "ID da VLAN (%%vlanid%%).",
            "backup_port": "Porta do backup SIP (%%backsipport%%).",
        }


class DeviceConfigForm(forms.ModelForm):
    """
    Form para DeviceConfig. Campos mapeados para placeholders:
      - identifier -> %%account%%
      - display_name -> %%displayname%%
      - user_register -> %%user%%
      - passwd_register -> %%passwd%%
      - mac_address -> %%macaddress%%
    """
    class Meta:
        model = DeviceConfig
        fields = [
            "profile",
            "identifier",
            "mac_address",
            "display_name",
            "user_register",
            "passwd_register",
            "ip_address",
            "public_ip",
            "private_ip",
        ]
        widgets = {
            "passwd_register": forms.PasswordInput(render_value=True),
        }
        help_texts = {
            "identifier": "Account usado no template (%%account%%).",
            "display_name": "Nome mostrado (%%displayname%%).",
            "user_register": "Usuário de registro (%%user%%).",
            "passwd_register": "Senha de registro (%%passwd%%).",
            "mac_address": "Endereço MAC (apenas hex) usado em %%macaddress%%.",
        }

    def clean_mac_address(self):
        val = self.cleaned_data.get("mac_address") or ""
        # permitir o form aceitar formatos com separadores, o model fará normalização ao salvar
        return val.strip()


DeviceFormSet = inlineformset_factory(
    DeviceProfile,
    DeviceConfig,
    form=DeviceConfigForm,
    fields=[
        "identifier",
        "mac_address",
        "display_name",
        "user_register",
        "passwd_register",
        "ip_address",
        "public_ip",
        "private_ip",
    ],
    extra=1,
    can_delete=True,
)