# mensajes/models.py
from django.db import models
from apps.leads.models import Lead
from apps.conversaciones.models import Conversacion

class Mensaje(models.Model):
    """Modelo para mensajes individuales"""
    
    TIPOS = [
        ('mensaje_directo', 'Mensaje Directo'),
        ('comentario_publico', 'Comentario Público'),
        ('respuesta', 'Respuesta'),
        ('nota_interna', 'Nota Interna'),
    ]
    
    INTENCIONES = [
        ('consulta', 'Consulta'),
        ('cotizacion', 'Cotización'),
        ('queja', 'Queja'),
        ('soporte', 'Soporte'),
        ('informacion', 'Información'),
        ('venta', 'Venta'),
        ('otro', 'Otro'),
    ]
    
    SENTIMIENTOS = [
        ('positivo', 'Positivo'), 
        ('neutro', 'Neutro'), 
        ('negativo', 'Negativo')
    ]
    
    lead = models.ForeignKey(
        Lead, 
        on_delete=models.CASCADE, 
        related_name='mensajes'
    )
    conversacion = models.ForeignKey(
        Conversacion,
        on_delete=models.CASCADE,
        related_name='mensajes',
        null=True,
        blank=True
    )
    plataforma = models.CharField(max_length=20, choices=Lead.PLATAFORMAS)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Flags de respuesta
    es_respuesta = models.BooleanField(default=False)
    respuesta_automatica = models.BooleanField(default=False)
    
    # NLP y análisis
    intencion_detectada = models.CharField(
        max_length=20, 
        choices=INTENCIONES, 
        null=True, 
        blank=True
    )
    sentimiento = models.CharField(
        max_length=10,
        choices=SENTIMIENTOS,
        null=True,
        blank=True
    )
    confianza_nlp = models.FloatField(null=True, blank=True, help_text="Confianza del análisis NLP (0-1)")
    
    # Metadata
    mensaje_original_id = models.CharField(max_length=100, null=True, blank=True)
    procesado = models.BooleanField(default=False)
    requiere_atencion = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'mensajes'
        verbose_name = 'Mensaje'
        verbose_name_plural = 'Mensajes'
        indexes = [
            models.Index(fields=['lead', 'fecha']),
            models.Index(fields=['conversacion', 'fecha']),
            models.Index(fields=['tipo']),
            models.Index(fields=['es_respuesta']),
            models.Index(fields=['requiere_atencion']),
        ]
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.lead.nombre or self.lead.plataforma_id}"
    
    def marcar_como_procesado(self):
        """Marcar mensaje como procesado"""
        self.procesado = True
        self.save(update_fields=['procesado'])
    
    @property
    def preview_contenido(self):
        """Obtiene un preview del contenido del mensaje"""
        return self.contenido[:100] + '...' if len(self.contenido) > 100 else self.contenido
    
    @property
    def tiempo_transcurrido(self):
        """Calcula el tiempo transcurrido desde el mensaje"""
        from django.utils import timezone
        delta = timezone.now() - self.fecha
        
        if delta.days > 0:
            return f"hace {delta.days} día{'s' if delta.days != 1 else ''}"
        elif delta.seconds > 3600:
            horas = delta.seconds // 3600
            return f"hace {horas} hora{'s' if horas != 1 else ''}"
        elif delta.seconds > 60:
            minutos = delta.seconds // 60
            return f"hace {minutos} minuto{'s' if minutos != 1 else ''}"
        else:
            return "hace unos segundos"

