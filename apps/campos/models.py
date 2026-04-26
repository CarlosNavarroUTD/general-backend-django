# apps/campos/models.py

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.teams.models import Team


class Campo(models.Model):
    """
    Define un campo personalizado para una entidad específica de un team.
    Ejemplo: team X define 'Prioridad' (tipo selección) para 'lead'.
    """

    TIPO_CHOICES = [
        ('texto',      'Texto'),
        ('numero',     'Número'),
        ('decimal',    'Decimal'),
        ('fecha',      'Fecha'),
        ('datetime',   'Fecha y hora'),
        ('booleano',   'Booleano'),
        ('seleccion',  'Selección (opciones)'),
        ('url',        'URL'),
        ('email',      'Email'),
        ('telefono',   'Teléfono'),
    ]

    ENTIDAD_CHOICES = [
        ('lead',      'Lead'),
        ('servicio',  'Servicio'),
        ('producto',  'Producto'),
        ('contacto',  'Contacto'),
        ('orden',     'Orden'),
        # Agrega más según tu sistema
    ]

    team       = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='campos')
    entidad    = models.CharField(max_length=50, choices=ENTIDAD_CHOICES)
    nombre     = models.CharField(max_length=100)
    clave      = models.SlugField(max_length=100, help_text="Clave interna sin espacios, ej: 'fecha_cierre'")
    tipo       = models.CharField(max_length=20, choices=TIPO_CHOICES, default='texto')
    requerido  = models.BooleanField(default=False)
    activo     = models.BooleanField(default=True)
    # Para tipo='seleccion': ["Opción A", "Opción B", ...]
    opciones   = models.JSONField(default=list, blank=True)
    orden      = models.PositiveIntegerField(default=0, help_text="Orden de aparición")
    creado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table        = 'campos'
        verbose_name    = 'Campo personalizado'
        verbose_name_plural = 'Campos personalizados'
        # Un team no puede tener dos campos con la misma clave en la misma entidad
        unique_together = [('team', 'entidad', 'clave')]
        ordering        = ['entidad', 'orden', 'nombre']

    def __str__(self):
        return f"[{self.entidad}] {self.nombre} ({self.tipo})"


class CampoValor(models.Model):
    """
    Almacena el valor de un Campo para cualquier objeto del sistema.
    Usa GenericForeignKey para apuntar a Lead, Servicio, Producto, etc.
    """

    campo        = models.ForeignKey(Campo, on_delete=models.CASCADE, related_name='valores')
    # GenericFK — apunta al objeto dueño del valor
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveIntegerField()
    objeto       = GenericForeignKey('content_type', 'object_id')
    # Todos los valores se guardan como texto; la conversión la hace el serializer
    valor        = models.TextField(blank=True, null=True)

    class Meta:
        db_table        = 'campos_valores'
        verbose_name    = 'Valor de campo'
        verbose_name_plural = 'Valores de campos'
        unique_together = [('campo', 'content_type', 'object_id')]

    def __str__(self):
        return f"{self.campo.clave} = {self.valor}"

    def valor_tipado(self):
        """Devuelve el valor convertido al tipo correcto."""
        tipo = self.campo.tipo
        v    = self.valor
        if v is None:
            return None
        try:
            if tipo == 'numero':   return int(v)
            if tipo == 'decimal':  return float(v)
            if tipo == 'booleano': return v.lower() in ('true', '1', 'sí', 'si', 'yes')
            return v  # texto, fecha, url, email, etc. — ya es string
        except (ValueError, TypeError):
            return v