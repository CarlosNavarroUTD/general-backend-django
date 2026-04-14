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

    giro = models.CharField(max_length=50, choices=GIRO_CHOICES)
    cliente = models.CharField(max_length=255)
    campana = models.CharField(max_length=255)
    formato = models.CharField(max_length=50, choices=FORMAT_CHOICES)
    duracion = models.IntegerField(help_text="Duración en días")
    impactos = models.IntegerField()
    engagement = models.FloatField(help_text="Porcentaje de engagement")
    roi = models.FloatField(help_text="Retorno sobre inversión")
    imagen = models.ImageField(upload_to='portafolio/')
    
    class Meta:
        verbose_name = 'Portafolio'
        verbose_name_plural = 'Portafolios'
    
    def __str__(self):
        return f"{self.cliente} - {self.campana}"