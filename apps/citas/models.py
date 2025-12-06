# apps/citas/models.py
from django.db import models
from django.core.exceptions import ValidationError
from apps.usuarios.models import Usuario
from apps.servicios.models import Servicio
from apps.teams.models import Team


class Cita(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    )
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='citas')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='citas')
    
    # Campos actualizados para manejar rangos de fecha/hora
    fecha_inicio = models.DateTimeField(help_text="Fecha y hora de inicio de la cita")
    fecha_fin = models.DateTimeField(help_text="Fecha y hora de fin de la cita")
    
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='citas')

    class Meta:
        db_table = 'citas'
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['fecha_inicio']
    
    def clean(self):
        """Validación para asegurar que fecha_fin sea posterior a fecha_inicio"""
        super().clean()
        if self.fecha_inicio and self.fecha_fin:
            if self.fecha_fin <= self.fecha_inicio:
                raise ValidationError({
                    'fecha_fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cita {self.usuario} - {self.fecha_inicio.strftime('%d/%m/%Y %H:%M')}"