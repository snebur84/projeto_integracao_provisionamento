from django.db import models
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator,
)
from django.utils import timezone


HEX_LOWER_REGEX = RegexValidator(
    regex=r'^[0-9a-f]{12,14}$',
    message='MAC address must contain only lowercase hexadecimal characters and length between 12 and 14.'
)


class DeviceConfig(models.Model):
    # Core identification fields (used by api.download_config)
    vendor = models.CharField("vendor", max_length=50, blank=True)
    model = models.CharField("model", max_length=50, blank=True)
    version = models.CharField("version", max_length=50, blank=True)
    identifier = models.CharField("identifier", max_length=100, unique=True)
    ip_address = models.GenericIPAddressField("ip address", null=True, blank=True)
    location = models.CharField("location", max_length=255, blank=True)

    # Network IP fields: public and private IPs reported by device/request
    public_ip = models.GenericIPAddressField("public ip", null=True, blank=True)
    private_ip = models.GenericIPAddressField("private ip", null=True, blank=True)

    # SIP related fields (conforme especificado)
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

    mac_address = models.CharField(
        "MAC address",
        max_length=14,
        unique=True,
        validators=[HEX_LOWER_REGEX],
        help_text="Apenas caracteres hexadecimais minúsculos (12 a 14 chars)."
    )

    user_register = models.CharField("user register", max_length=21, blank=True)
    passwd_register = models.CharField("passwd register", max_length=50, blank=True)
    display_name = models.CharField("display name", max_length=50, blank=True)
    display_number = models.CharField("display number", max_length=50, blank=True)
    backup_server = models.CharField("backup server", max_length=50, blank=True)
    domain_server = models.CharField("domain server", max_length=50, blank=True)
    time_zone = models.CharField("time zone", max_length=50, blank=True)
    srtp_enable = models.BooleanField("SRTP enabled", default=False)

    # Timestamps and provisioning metadata (nomes "renomeados adequadamente")
    created_at = models.DateTimeField("created at", auto_now_add=True)
    updated_at = models.DateTimeField("updated at", auto_now=True)
    provisioned_at = models.DateTimeField("provisioned at", null=True, blank=True)
    attempts_provisioning = models.PositiveIntegerField("attempts provisioning", default=0)
    exported_to_rps = models.BooleanField("exported to RPS", default=False)

    class Meta:
        verbose_name = "Device configuration"
        verbose_name_plural = "Device configurations"
        ordering = ["-created_at"]

    def __str__(self):
        if self.identifier:
            return f"{self.identifier} ({self.model or 'unknown model'})"
        return f"DeviceConfig #{self.pk}"

    def clean(self):
        # Normalização: garantir MAC em minúsculas sem separadores
        if self.mac_address:
            self.mac_address = self.mac_address.strip().lower()
        super().clean()

    def mark_provisioned(self):
        """
        Helper to mark device as provisioned now and reset attempts.
        """
        self.provisioned_at = timezone.now()
        self.attempts_provisioning = 0
        self.save(update_fields=["provisioned_at", "attempts_provisioning"])