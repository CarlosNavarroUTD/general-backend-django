# apps/integraciones/models.py

from django.db import models
from apps.teams.models import Team  # o el nombre del modelo que uses
from apps.usuarios.models import Usuario
from django.utils.timezone import now, timedelta

class GoogleToken(models.Model):
    user = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def is_expired(self):
        return now() >= self.expires_at

class GoogleMapsIntegration(models.Model):
    team = models.OneToOneField(Team, on_delete=models.CASCADE, related_name="google_maps_integration")
    place_id = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team.name} - Google Maps Integration"


class GooglePlaceBusiness(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="google_businesses")
    name = models.CharField(max_length=255)
    place_id = models.CharField(max_length=255, unique=True)
    address = models.TextField(null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True) 
    website = models.URLField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    user_ratings_total = models.IntegerField(null=True, blank=True)
    business_status = models.CharField(max_length=50, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['team', 'place_id']

    def __str__(self):
        return f"{self.team.name} - {self.name}"

class WhatsappInstance(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="whatsapp_instances")
    instance_name = models.CharField(max_length=255)
    instance_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    token = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=50, default="disconnected") # connected, disconnected, qr_pending
    phone_number = models.CharField(max_length=50, null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

class GoogleSheetIntegration(models.Model):
    ENTIDAD_CHOICES = [
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="googlesheet_integrations")
    spreadsheet_id = models.CharField(max_length=255)
    sheet_name = models.CharField(max_length=100, default="Sheet1")
    entidad = models.CharField(max_length=20, choices=ENTIDAD_CHOICES)
    
    # Mapeo: {"campo_sistema": "nombre_columna_sheet"}
    # Ejemplo: {"nombre": "Producto", "precio": "Precio Venta", "sku": "Código"}
    mapping = models.JSONField(default=dict, help_text="Mapeo de campos del sistema a columnas del Sheet")
    
    # Identificadores: ["sku"] o ["nombre"]
    identificadores = models.JSONField(default=list, help_text="Campos usados para verificar si el registro ya existe")
    
    last_sync = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.team.name} - Google Sheet ({self.entidad})"