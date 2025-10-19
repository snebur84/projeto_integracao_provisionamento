from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class DeviceProfile(models.Model):
    """
    Perfil de dispositivo (campos comuns entre dispositivos do mesmo perfil).
    Template_ref refere-se ao documento no MongoDB (p.ex. um _id string ou um nome model.ext).
    """
    name = models.CharField("profile name", max_length=150, unique=True)
    sip_server = models.CharField("SIP server", max_length=50, blank=True)
    port_server = models.IntegerField(
        "port server",
        validators=[MinValueValidator(1000), MaxValueValidator(9999)],
        default=5060,
        help_text="Porta com 4 dígitos (entre 1000 e 9999)."
    )

    PROTOCOL_UDP = "UDP"
    PROTOCOL_TCP = "TCP"
    PROTOCOL_TLS = "TLS"
    PROTOCOL_CHOICES = [
        (PROTOCOL_UDP, "UDP"),
        (PROTOCOL_TCP, "TCP"),
        (PROTOCOL_TLS, "TLS"),
    ]
    protocol_type = models.CharField(
        "protocol type",
        max_length=3,
        choices=PROTOCOL_CHOICES,
        default=PROTOCOL_UDP,
    )
    backup_server = models.CharField("backup server", max_length=50, blank=True)
    domain_server = models.CharField("domain server", max_length=50, blank=True)
    time_zone = models.CharField("time zone", max_length=50, blank=True)
    srtp_enable = models.BooleanField("SRTP enabled", default=False)
    # referência para template armazenado no MongoDB; pode ser um _id ou um identificador único
    template_ref = models.CharField("template ref", max_length=255, blank=True, help_text="Identificador do template no MongoDB")

    # metadata livre para extensões/integrações
    metadata = models.JSONField("metadata", blank=True, null=True, default=dict)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "Device Profile"
        verbose_name_plural = "Device Profiles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class DeviceConfig(models.Model):
    """
    Entidade que representa um dispositivo específico (estado atual).
    Campos 'comuns' movidos para DeviceProfile; aqui ficam campos por-dispositivo.
    """
    profile = models.ForeignKey(DeviceProfile, related_name="devices", on_delete=models.SET_NULL, null=True, blank=True)
    identifier = models.CharField("identifier", max_length=255, unique=True, help_text="Identificador lógico do device")
    mac_address = models.CharField("mac address", max_length=32, unique=True, db_index=True)
    user_register = models.CharField("user register", max_length=21, blank=True)
    passwd_register = models.CharField("passwd register", max_length=50, blank=True)
    display_name = models.CharField("display name", max_length=50, blank=True)

    # estado resumido / denormalizado
    ip_address = models.GenericIPAddressField("ip address", null=True, blank=True)
    public_ip = models.GenericIPAddressField("public ip", null=True, blank=True)
    private_ip = models.GenericIPAddressField("private ip", null=True, blank=True)

    attempts_provisioning = models.PositiveIntegerField("attempts provisioning", default=0)
    provisioned_at = models.DateTimeField("provisioned at", null=True, blank=True)
    exported_to_rps = models.BooleanField("exported to RPS", default=False)

    metadata = models.JSONField("metadata", blank=True, null=True, default=dict)

    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)

    class Meta:
        verbose_name = "Device Config"
        verbose_name_plural = "Device Configs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["mac_address"]),
            models.Index(fields=["identifier"]),
        ]

    def __str__(self):
        return self.identifier or self.mac_address


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