# leads/models.py
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from django.utils import timezone
from apps.teams.models import Team

class Lead(models.Model):
    """Modelo principal para leads/prospectos"""
    
    PLATAFORMAS = [
        ('whatsapp', 'WhatsApp'),
        ('facebook', 'Facebook'),
        ('instagram', 'Instagram'),
        ('google_maps', 'Google Maps'),
        ('linkedin', 'LinkedIn'),
        ('twitter', 'Twitter'),
        ('web', 'Sitio Web'),
        ('otro', 'Otro'),
    ]
    
    ESTADOS = [
        ('nuevo', 'Nuevo'),
        ('contactado', 'Contactado'),
        ('en_seguimiento', 'En Seguimiento'),
        ('convertido', 'Convertido'),
        ('perdido', 'Perdido'),
    ]
    
    FUENTES = [
        ('comentario', 'Comentario'),
        ('mensaje_directo', 'Mensaje Directo'),
        ('mencion', 'Mención'),
        ('formulario', 'Formulario'),
        ('referido', 'Referido'),
        ('llamada', 'Llamada'),
        ('otro', 'Otro'),
    ]
    
    # Validador para teléfono
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="El teléfono debe estar en formato: '+999999999'. Hasta 15 dígitos."
    )
    
    nombre = models.CharField(max_length=150, blank=True, null=True)
    plataforma = models.CharField(max_length=20, choices=PLATAFORMAS)
    plataforma_id = models.CharField(max_length=100, help_text="ID del usuario en la plataforma")
    telefono = models.CharField(
        validators=[phone_regex], 
        max_length=17, 
        blank=True, 
        null=True
    )
    email = models.EmailField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='nuevo')
    fuente = models.CharField(max_length=20, choices=FUENTES)
    asignado_a = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='leads_asignados'
    )
    
    # Campos adicionales para tracking
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    ultima_interaccion = models.DateTimeField(default=timezone.now)
    notas = models.TextField(blank=True)
    
    # Campos para métricas
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    probabilidad_conversion = models.IntegerField(default=0, help_text="Porcentaje de 0 a 100")
    
    class Meta:
        db_table = 'leads'
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        indexes = [
            models.Index(fields=['plataforma', 'plataforma_id']),
            models.Index(fields=['estado']),
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['asignado_a']),
        ]
        unique_together = ['plataforma', 'plataforma_id']
    
    def __str__(self):
        return f"{self.nombre or 'Sin nombre'} - {self.get_plataforma_display()}"
    
    @property
    def mensajes_count(self):
        # Importación lazy para evitar dependencias circulares
        from mensajes.models import Mensaje
        return Mensaje.objects.filter(lead=self).count()
    
    @property
    def ultima_conversacion(self):
        # Importación lazy para evitar dependencias circulares
        from conversaciones.models import Conversacion
        return Conversacion.objects.filter(lead=self, estado='abierto').first()

class ActividadLead(models.Model):
    """Modelo para tracking de actividades en leads"""
    
    TIPOS_ACTIVIDAD = [
        ('creacion', 'Creación'),
        ('actualizacion', 'Actualización'),
        ('asignacion', 'Asignación'),
        ('cambio_estado', 'Cambio de Estado'),
        ('nota', 'Nota Agregada'),
        ('mensaje', 'Mensaje Enviado'),
        ('llamada', 'Llamada'),
        ('reunion', 'Reunión'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='actividades')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_ACTIVIDAD)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'actividades_lead'
        verbose_name = 'Actividad de Lead'
        verbose_name_plural = 'Actividades de Lead'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.lead}"
