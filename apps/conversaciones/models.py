# conversaciones/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.teams.models import Team
from apps.leads.models import Lead


class Conversacion(models.Model):
    """Modelo para hilos de conversación"""
    
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
        ('en_seguimiento', 'En Seguimiento'),
    ]
    
    lead = models.ForeignKey(
        Lead, 
        on_delete=models.CASCADE, 
        related_name='conversaciones'
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto')
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='conversaciones_asignadas'
    )
    equipo_asignado = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversaciones_asignadas'
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    
    # Métricas de conversación
    tiempo_respuesta_promedio = models.DurationField(null=True, blank=True)
    satisfaccion_cliente = models.IntegerField(null=True, blank=True, help_text="1-5 estrellas")
    
    class Meta:
        db_table = 'conversaciones'
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'
        indexes = [
            models.Index(fields=['lead', 'estado']),
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['asignado_a']),
        ]
        ordering = ['-fecha_actualizacion']
    
    def __str__(self):
        return f"Conversación con {self.lead.nombre or self.lead.plataforma_id}"
    
    def cerrar_conversacion(self):
        """Método para cerrar una conversación"""
        self.estado = 'cerrado'
        self.fecha_cierre = timezone.now()
        self.save()
    
    @property
    def duracion_conversacion(self):
        """Calcula la duración de la conversación"""
        fecha_fin = self.fecha_cierre or timezone.now()
        return fecha_fin - self.fecha_creacion
    
    @property
    def total_mensajes(self):
        """Cuenta el total de mensajes en la conversación"""
        return self.mensajes.count()
    
    @property
    def ultimo_mensaje(self):
        """Obtiene el último mensaje de la conversación"""
        return self.mensajes.first()  # Ya está ordenado por -fecha

    @classmethod
    def create_for_flow(cls, lead, **kwargs):
        """
        Crea una conversación inicial para un flow.
        kwargs se usa para pasar información extra opcional sin romper la creación.
        """
        return cls.objects.create(lead=lead)
