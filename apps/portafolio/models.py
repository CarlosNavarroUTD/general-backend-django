from django.db import models

from apps.teams.models import Team

class Portafolio(models.Model):
    GIRO_CHOICES = [
        ('tecnologia', 'Tecnología'),
        ('retail', 'Retail'),
        ('finanzas', 'Finanzas'),
        ('salud', 'Salud'),
        ('educacion', 'Educación'),
    ]
    
    FORMAT_CHOICES = [
        ('video', 'Video'),
        ('imagen', 'Imagen'),
        ('banner', 'Banner'),
        ('texto', 'Texto'),
    ]
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='notas'
    )
    
    disponible = models.BooleanField(default=True)

    giro = models.CharField(max_length=50)

    cliente = models.CharField(max_length=255,blank=True, null=True)
    campana = models.CharField(max_length=255, blank=True, null=True)
    formato = models.CharField(max_length=50,blank=True, null=True)
    duracion = models.CharField(max_length=50, blank=True, null=True)
    impactos = models.CharField(max_length=50, blank=True, null=True)
    engagement = models.CharField(max_length=50, blank=True, null=True)
    roi = models.CharField(max_length=50, blank=True, null=True)
    imagen = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        verbose_name = 'Portafolio'
        verbose_name_plural = 'Portafolios'
    
    def __str__(self):
        return f"{self.cliente} - {self.campana}"