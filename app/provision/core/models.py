from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import re


def _normalize_mac(value: str) -> str:
    """Normalize MAC to lowercase hex without separators. Returns empty string if None/empty."""
    if not value:
        return ""
    v = value.strip().lower()
    v = re.sub(r'[^0-9a-f]', '', v)
    return v


class DeviceProfile(models.Model):
    """
    Perfil de dispositivo (campos comuns entre dispositivos do mesmo perfil).
    Campos adicionais mapeiam placeholders encontrados nos templates:
      - provision_server / provision_file / ntp_server / voice_codecs / vlan_active / vlan_id / proxy / register_ttl
    The collection template_ref references a document in MongoDB (e.g. a template _id).
    """
    name = models.CharField("profile name", max_length=150, unique=True)

    # SIP / provisioning related
    sip_server = models.CharField("SIP server", max_length=255, blank=True)
    port_server = models.IntegerField(
        "port server",
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        default=5060,
        help_text="Porta do servidor SIP"
    )
    protocol_type = models.CharField(
        "protocol type",
        max_length=4,
        choices=[("UDP", "UDP"), ("TCP", "TCP"), ("TLS", "TLS")],
        default="UDP",
    )

    # Backup server and port (backsipserver / backsipport)
    backup_server = models.CharField("Backup SIP server", max_length=255, blank=True)
    backup_port = models.IntegerField("Backup SIP port", default=5060, validators=[MinValueValidator(1), MaxValueValidator(65535)])

    # Proxy used by devices (%%proxy%%)
    proxy = models.CharField("Proxy address", max_length=255, blank=True)

    # Domain / local domain (%%domain%%)
    domain_server = models.CharField("Domain / Local domain", max_length=255, blank=True)

    # Registration TTL (%%registerttl%%)
    register_ttl = models.IntegerField("Register TTL", default=3600, help_text="Default registation TTL in seconds")

    # Voice codecs list used in template (%%codecs%%) - stored comma-separated
    voice_codecs = models.CharField("Voice codecs", max_length=255, blank=True, help_text="Comma separated codecs, e.g. PCMU,PCMA,G729")

    # NTP server (%%ntpserver%%)
    ntp_server = models.CharField("NTP server", max_length=255, blank=True)

    # Provisioning server / file placeholders
    provision_server = models.CharField("Provision server", max_length=255, blank=True)
    provision_file = models.CharField("Provision file", max_length=255, blank=True)

    # VLAN settings (%%vlanactive%% bool, %%vlanid%% int)
    vlan_active = models.BooleanField("VLAN active", default=False)
    vlan_id = models.IntegerField("VLAN ID", null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(4094)])

    # SRTP, timezone, template_ref and metadata (existing)
    time_zone = models.CharField("time zone", max_length=50, blank=True)
    srtp_enable = models.BooleanField("SRTP enabled", default=False)
    template_ref = models.CharField("Mongo template reference", max_length=255, blank=True, help_text="Mongo template _id or identifier")
    metadata = models.JSONField("metadata", default=dict, blank=True)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        ordering = ("name",)
        verbose_name = "Device profile"
        verbose_name_plural = "Device profiles"

    def __str__(self) -> str:
        return self.name


class DeviceConfig(models.Model):
    """
    Representa um dispositivo (instância) associado a um DeviceProfile.

    Este model expõe propriedades auxiliares para mapear os placeholders do template:
      - account -> identifier    (%%account%%)
      - displayname -> display_name (%%displayname%%)
      - user -> user_register    (%%user%%)
      - passwd -> passwd_register (%%passwd%%)
      - macaddress property proxies mac_address (%%macaddress%%)
    """
    profile = models.ForeignKey(DeviceProfile, related_name="devices", on_delete=models.SET_NULL, null=True, blank=True)

    # identifier/logical account (PhoneNumber in template)
    identifier = models.CharField("identifier", max_length=255, unique=True, help_text="Logical identifier / account (used as %%account%%)")

    mac_address = models.CharField("mac address", max_length=32, unique=True, db_index=True, help_text="Normalized MAC (only hex)")

    user_register = models.CharField("user register", max_length=128, blank=True, help_text="User (%%user%%)")
    passwd_register = models.CharField("passwd register", max_length=128, blank=True, help_text="Password (%%passwd%%)")

    display_name = models.CharField("display name", max_length=100, blank=True, help_text="Display name (%%displayname%%)")

    # IP/state fields
    ip_address = models.GenericIPAddressField("ip address", null=True, blank=True)
    public_ip = models.GenericIPAddressField("public ip", null=True, blank=True)
    private_ip = models.GenericIPAddressField("private ip", null=True, blank=True)

    # State / bookkeeping
    provisioned_at = models.DateTimeField("provisioned at", null=True, blank=True)
    attempts_provisioning = models.IntegerField("attempts provisioning", default=0)
    exported_to_rps = models.BooleanField("exported to RPS", default=False)

    metadata = models.JSONField("metadata", default=dict, blank=True)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        ordering = ("identifier",)
        verbose_name = "Device config"
        verbose_name_plural = "Device configs"

    def __str__(self) -> str:
        return self.identifier or self.mac_address or "<unnamed device>"

    def save(self, *args, **kwargs):
        # normalize mac_address before saving
        if self.mac_address:
            self.mac_address = _normalize_mac(self.mac_address)
        super().save(*args, **kwargs)

    # --- convenience properties to map template placeholders to model fields ---

    @property
    def account(self) -> str:
        """Maps to identifier (%%account%%)"""
        return self.identifier

    @account.setter
    def account(self, value: str) -> None:
        self.identifier = (value or "").strip()

    @property
    def displayname(self) -> str:
        """Maps to display_name (%%displayname%%)"""
        return self.display_name

    @displayname.setter
    def displayname(self, value: str) -> None:
        self.display_name = (value or "").strip()

    @property
    def user(self) -> str:
        """Maps to user_register (%%user%%)"""
        return self.user_register

    @user.setter
    def user(self, value: str) -> None:
        self.user_register = (value or "").strip()

    @property
    def passwd(self) -> str:
        """Maps to passwd_register (%%passwd%%)"""
        return self.passwd_register

    @passwd.setter
    def passwd(self, value: str) -> None:
        self.passwd_register = (value or "").strip()

    @property
    def macaddress(self) -> str:
        """Convenience access to normalized mac address (%%macaddress%%)."""
        return self.mac_address

    @macaddress.setter
    def macaddress(self, value: str) -> None:
        self.mac_address = _normalize_mac(value or "")



class Provisioning(models.Model):
    """
    Registro de cada tentativa de provisionamento / evento.
    Mantém FK para DeviceConfig (se disponível) e copia denormalizada do mac/identifier.
    """
    STATUS_OK = "ok"
    STATUS_FORBIDDEN = "forbidden"
    STATUS_ERROR = "error"
    STATUS_CHOICES = [
        (STATUS_OK, "OK"),
        (STATUS_FORBIDDEN, "Forbidden"),
        (STATUS_ERROR, "Error"),
    ]

    device = models.ForeignKey(DeviceConfig, related_name="provisionings", on_delete=models.CASCADE, null=True, blank=True)
    mac_address = models.CharField("mac address", max_length=32, blank=True, db_index=True)
    identifier = models.CharField("identifier", max_length=255, blank=True, db_index=True)

    vendor = models.CharField("vendor", max_length=50, blank=True)
    model = models.CharField("model", max_length=50, blank=True)
    version = models.CharField("version", max_length=50, blank=True)

    public_ip = models.GenericIPAddressField("public ip", null=True, blank=True)
    private_ip = models.GenericIPAddressField("private ip", null=True, blank=True)

    filename = models.CharField("filename", max_length=255, blank=True)
    template_ref = models.CharField("template ref", max_length=255, blank=True)
    status = models.CharField("status", max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)

    user_agent = models.TextField("user agent", blank=True)
    notes = models.TextField("notes", blank=True)

    metadata = models.JSONField("metadata", blank=True, null=True, default=dict)

    created_at = models.DateTimeField("created at", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "Provisioning"
        verbose_name_plural = "Provisionings"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["mac_address"]),
        ]

    def __str__(self):
        when = self.created_at.isoformat() if self.created_at else "unknown"
        return f"{self.mac_address or self.identifier} @ {when}"