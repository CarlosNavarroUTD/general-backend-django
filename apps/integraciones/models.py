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