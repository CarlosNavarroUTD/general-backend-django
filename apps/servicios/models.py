# apps/servicios/models.py
from django.db import models
from apps.teams.models import Team
from utils.generate_radom_code import generar_codigo


class CampoPersonalizado(models.Model):
    """
    Define la estructura de un campo personalizado para un team.
    Actúa como una "plantilla" o "definición" del campo.
    """
    TIPO_TEXTO = 'text'
    TIPO_NUMERO = 'number'
    TIPO_FECHA = 'date'
    TIPO_BOOLEANO = 'boolean'

    TIPOS = [
        (TIPO_TEXTO, 'Texto'),
        (TIPO_NUMERO, 'Número'),
        (TIPO_FECHA, 'Fecha'),
        (TIPO_BOOLEANO, 'Booleano'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    requerido = models.BooleanField(default=False)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='campos_personalizados'
    )
    personalizado_id = models.CharField(
        max_length=6,
        unique=True,
        default=generar_codigo,
        editable=False
    )

    class Meta:
        db_table = 'campos_personalizados'
        verbose_name = 'Campo Personalizado'
        verbose_name_plural = 'Campos Personalizados'

    def __str__(self):
        return f"{self.nombre} [{self.get_tipo_display()}] — {self.team}"


class Servicio(models.Model):
    """
    Representa un servicio. Los valores de campos personalizados
    se almacenan a través de ServicioCampoValor.
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    duracion = models.IntegerField(help_text="Duración en minutos")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='servicios')
    url_img = models.URLField(blank=True, null=True)

    class Meta:
        db_table = 'servicios'
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'

    def __str__(self):
        return self.nombre


class ServicioCampoValor(models.Model):
    """
    Tabla pivote que almacena el VALOR de un CampoPersonalizado
    para un Servicio específico.

    Un campo puede ser de tipo texto, número, fecha o booleano,
    por lo que se usa una columna por tipo y solo se llena la correspondiente.
    """
    servicio = models.ForeignKey(
        Servicio,
        on_delete=models.CASCADE,
        related_name='campos_valores'
    )
    campo = models.ForeignKey(
        CampoPersonalizado,
        on_delete=models.CASCADE,
        related_name='valores'
    )

    # Solo se llena la columna correspondiente al tipo del campo
    valor_texto = models.TextField(null=True, blank=True)
    valor_numero = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    valor_fecha = models.DateField(null=True, blank=True)
    valor_booleano = models.BooleanField(null=True, blank=True)

    class Meta:
        db_table = 'servicio_campo_valores'
        verbose_name = 'Valor de Campo'
        verbose_name_plural = 'Valores de Campos'
        # Un campo solo puede tener un valor por servicio
        unique_together = ('servicio', 'campo')

    def __str__(self):
        return f"{self.servicio.nombre} → {self.campo.nombre}: {self.valor}"

    @property
    def valor(self):
        """Devuelve el valor según el tipo del campo asociado."""
        tipo = self.campo.tipo
        if tipo == CampoPersonalizado.TIPO_TEXTO:
            return self.valor_texto
        if tipo == CampoPersonalizado.TIPO_NUMERO:
            return self.valor_numero
        if tipo == CampoPersonalizado.TIPO_FECHA:
            return str(self.valor_fecha) if self.valor_fecha else None
        if tipo == CampoPersonalizado.TIPO_BOOLEANO:
            return self.valor_booleano
        return None