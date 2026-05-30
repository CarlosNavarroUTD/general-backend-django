from django.db import models
from apps.teams.models import Team
from apps.leads.models import Lead
from apps.integraciones.models import WhatsappInstance

class Plantilla(models.Model):
    nombre = models.CharField(max_length=255)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='plantillas')
    contenido = models.TextField(help_text="Texto de la plantilla. Puede incluir variables como {{nombre}}")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} ({self.team.name})"

class Campana(models.Model):
    ESTADOS = (
        ('borrador', 'Borrador'),
        ('enviando', 'Enviando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    )

    nombre = models.CharField(max_length=255)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='campanas')
    plantilla = models.ForeignKey(Plantilla, on_delete=models.SET_NULL, null=True, related_name='campanas')
    whatsapp_instance = models.ForeignKey(WhatsappInstance, on_delete=models.SET_NULL, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"

class CampanaLead(models.Model):
    ESTADOS_ENVIO = (
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('error', 'Error'),
    )

    campana = models.ForeignKey(Campana, on_delete=models.CASCADE, related_name='campana_leads')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='campana_leads')
    estado_envio = models.CharField(max_length=20, choices=ESTADOS_ENVIO, default='pendiente')
    mensaje_error = models.TextField(blank=True, null=True)
    enviado_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ('campana', 'lead')

    def __str__(self):
        return f"{self.campana.nombre} -> {self.lead.nombre or self.lead.telefono} ({self.get_estado_envio_display()})"
