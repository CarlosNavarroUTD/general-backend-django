from django.db import models
from django.conf import settings
from apps.teams.models import Team
from apps.servicios.models import Servicio

User = settings.AUTH_USER_MODEL

class Nota(models.Model):
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notas'
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='notas'
    )

    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas'
    )

    titulo = models.CharField(max_length=255)
    contenido = models.TextField()

    es_publica = models.BooleanField(default=False)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    activa = models.BooleanField(default=True)

    class Meta:
        db_table = 'notas'
        ordering = ['-creada_en']

    def __str__(self):
        return self.titulo