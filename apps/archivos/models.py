from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
import uuid
import hashlib

User = get_user_model()


class Archivo(models.Model):
    """
    Modelo para almacenar archivos subidos por el equipo
    """
    TIPO_ARCHIVO_CHOICES = [
        ('contrato', 'Contrato'),
        ('documento', 'Documento'),
        ('imagen', 'Imagen'),
        ('otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='archivos')
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    archivo = models.FileField(
        upload_to='archivos/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'xlsx', 'csv', 'gif', 'webp'])]
    )
    tipo_archivo = models.CharField(max_length=20, choices=TIPO_ARCHIVO_CHOICES, default='documento')
    
    # Metadatos
    tamano = models.BigIntegerField(help_text="Tamaño en bytes", null=True, blank=True)
    hash_sha256 = models.CharField(max_length=64, blank=True, help_text="Hash SHA-256 del archivo para verificación de integridad")
    
    # Auditoría
    subido_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='archivos_subidos')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Seguridad
    es_privado = models.BooleanField(default=False)
    requiere_autenticacion = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Archivo'
        verbose_name_plural = 'Archivos'
        ordering = ['-fecha_subida']
        indexes = [
            models.Index(fields=['team', '-fecha_subida']),
            models.Index(fields=['hash_sha256']),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.team.nombre}"


class AccesoArchivo(models.Model):
    """
    Modelo para registrar accesos a archivos (auditoría)
    """
    TIPO_ACCESO_CHOICES = [
        ('visualizacion', 'Visualización'),
        ('descarga', 'Descarga'),
        ('modificacion', 'Modificación'),
        ('eliminacion', 'Eliminación'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    archivo = models.ForeignKey(Archivo, on_delete=models.CASCADE, related_name='accesos')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    tipo_acceso = models.CharField(max_length=20, choices=TIPO_ACCESO_CHOICES)
    
    # Información de la sesión
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp
    fecha_acceso = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Acceso a Archivo'
        verbose_name_plural = 'Accesos a Archivos'
        ordering = ['-fecha_acceso']
        indexes = [
            models.Index(fields=['archivo', '-fecha_acceso']),
            models.Index(fields=['usuario', '-fecha_acceso']),
        ]

    def __str__(self):
        usuario_str = self.usuario.email if self.usuario else "Anónimo"
        return f"{self.archivo.nombre} - {self.tipo_acceso} por {usuario_str}"