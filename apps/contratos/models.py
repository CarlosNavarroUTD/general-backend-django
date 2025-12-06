from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils.crypto import get_random_string
from django.utils import timezone
import uuid
import hashlib
import json

User = get_user_model()


def generar_token_unico():
    """Genera un token único de 32 caracteres"""
    return get_random_string(32)


class Contrato(models.Model):
    """
    Modelo principal para contratos con firmas digitales
    """
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('activo', 'Activo - Esperando Firmas'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
        ('expirado', 'Expirado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE, related_name='contratos')
    
    # Información básica
    titulo = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    
    # Documento PDF
    documento_original = models.FileField(
        upload_to='contratos/originales/%Y/%m/%d/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    documento_firmado = models.FileField(
        upload_to='contratos/firmados/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Documento con todas las firmas aplicadas"
    )
    
    # Metadatos del documento
    hash_documento_original = models.CharField(max_length=64, help_text="Hash SHA-256 del documento original")
    hash_documento_firmado = models.CharField(max_length=64, blank=True, null=True, help_text="Hash SHA-256 del documento firmado")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    
    # Tokens de acceso
    token_formulario = models.CharField(max_length=32, unique=True, default=generar_token_unico, help_text="Token para acceder al formulario de datos")
    token_visualizacion = models.CharField(max_length=32, unique=True, default=generar_token_unico, help_text="Token para visualizar y firmar el contrato")
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_activacion = models.DateTimeField(null=True, blank=True)
    fecha_expiracion = models.DateTimeField(null=True, blank=True)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contratos_creados')
    
    # Configuración de seguridad
    requiere_autenticacion_doble = models.BooleanField(default=False, help_text="Requiere código de verificación por email")
    ip_permitidas = models.TextField(blank=True, help_text="IPs permitidas separadas por comas (vacío = todas)")
    limite_intentos_firma = models.IntegerField(default=3)
    
    # Configuración de notificaciones
    email_notificacion = models.EmailField(blank=True, help_text="Email para recibir notificaciones de firmas")
    notificar_cada_firma = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['team', '-fecha_creacion']),
            models.Index(fields=['estado']),
            models.Index(fields=['token_formulario']),
            models.Index(fields=['token_visualizacion']),
        ]

    def __str__(self):
        return f"{self.titulo} - {self.get_estado_display()}"

    def save(self, *args, **kwargs):
        # Calcular hash del documento original
        if self.documento_original and not self.hash_documento_original:
            sha256_hash = hashlib.sha256()
            for chunk in self.documento_original.chunks():
                sha256_hash.update(chunk)
            self.hash_documento_original = sha256_hash.hexdigest()
        
        # Calcular hash del documento firmado
        if self.documento_firmado and not self.hash_documento_firmado:
            sha256_hash = hashlib.sha256()
            for chunk in self.documento_firmado.chunks():
                sha256_hash.update(chunk)
            self.hash_documento_firmado = sha256_hash.hexdigest()
            
        super().save(*args, **kwargs)

    def esta_expirado(self):
        """Verifica si el contrato ha expirado"""
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return True
        return False

    def puede_firmar(self):
        """Verifica si el contrato puede ser firmado"""
        return self.estado == 'activo' and not self.esta_expirado()

    def todas_firmas_completadas(self):
        """Verifica si todas las firmas requeridas están completadas"""
        campos_firma = self.campos.filter(tipo_campo='firma')
        return all(campo.firmado for campo in campos_firma)


class CampoContrato(models.Model):
    """
    Campos dinámicos del contrato (fechas, nombres, DNI, firmas, etc.)
    """
    TIPO_CAMPO_CHOICES = [
        ('texto', 'Texto'),
        ('fecha', 'Fecha'),
        ('dni', 'DNI/Identificación'),
        ('email', 'Email'),
        ('telefono', 'Teléfono'),
        ('firma', 'Firma Digital'),
        ('iniciales', 'Iniciales'),
        ('checkbox', 'Checkbox'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='campos')
    
    # Información del campo
    nombre_campo = models.CharField(max_length=100, help_text="Nombre identificador del campo (ej: 'nombre_firmante')")
    etiqueta = models.CharField(max_length=200, help_text="Etiqueta visible para el usuario")
    tipo_campo = models.CharField(max_length=20, choices=TIPO_CAMPO_CHOICES)
    
    # Posición en el PDF (coordenadas)
    pagina = models.IntegerField(help_text="Número de página donde se coloca el campo")
    posicion_x = models.FloatField(help_text="Posición X en el PDF (porcentaje)")
    posicion_y = models.FloatField(help_text="Posición Y en el PDF (porcentaje)")
    ancho = models.FloatField(help_text="Ancho del campo (porcentaje)")
    alto = models.FloatField(help_text="Alto del campo (porcentaje)")
    
    # Valor del campo
    valor = models.TextField(blank=True, help_text="Valor del campo (texto, fecha, etc.)")
    
    # Para firmas digitales
    firma_imagen = models.ImageField(
        upload_to='contratos/firmas/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Imagen de la firma dibujada"
    )
    firma_hash = models.CharField(max_length=64, blank=True, help_text="Hash de la firma para verificación")
    firmado = models.BooleanField(default=False)
    fecha_firma = models.DateTimeField(null=True, blank=True)
    ip_firma = models.GenericIPAddressField(null=True, blank=True)
    
    # Validación
    requerido = models.BooleanField(default=True)
    validacion_regex = models.CharField(max_length=200, blank=True, help_text="Regex para validar el campo")
    mensaje_ayuda = models.TextField(blank=True)
    
    # Orden
    orden = models.IntegerField(default=0, help_text="Orden de aparición en el formulario")
    
    class Meta:
        verbose_name = 'Campo de Contrato'
        verbose_name_plural = 'Campos de Contrato'
        ordering = ['contrato', 'orden']
        indexes = [
            models.Index(fields=['contrato', 'orden']),
        ]

    def __str__(self):
        return f"{self.contrato.titulo} - {self.etiqueta}"

    def save(self, *args, **kwargs):
        # Calcular hash de la firma si existe
        if self.firma_imagen and not self.firma_hash:
            sha256_hash = hashlib.sha256()
            for chunk in self.firma_imagen.chunks():
                sha256_hash.update(chunk)
            self.firma_hash = sha256_hash.hexdigest()
            self.firmado = True
            self.fecha_firma = timezone.now()
            
        super().save(*args, **kwargs)


class FirmanteContrato(models.Model):
    """
    Modelo para representar a los firmantes de un contrato
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('rechazado', 'Rechazado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='firmantes')
    
    # Información del firmante
    nombre_completo = models.CharField(max_length=255)
    email = models.EmailField()
    telefono = models.CharField(max_length=20, blank=True)
    dni = models.CharField(max_length=50, blank=True, help_text="DNI/Pasaporte/Identificación")
    
    # Estado
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # Token único para este firmante
    token_acceso = models.CharField(max_length=32, unique=True, default=generar_token_unico)
    
    # Código de verificación (si se requiere autenticación doble)
    codigo_verificacion = models.CharField(max_length=6, blank=True)
    codigo_verificacion_expira = models.DateTimeField(null=True, blank=True)
    intentos_verificacion = models.IntegerField(default=0)
    
    # Auditoría
    fecha_completado = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Consentimiento
    acepta_terminos = models.BooleanField(default=False)
    fecha_aceptacion_terminos = models.DateTimeField(null=True, blank=True)
    
    # Timestamp
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_invitacion_enviada = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Firmante'
        verbose_name_plural = 'Firmantes'
        ordering = ['contrato', 'fecha_creacion']
        indexes = [
            models.Index(fields=['contrato', 'estado']),
            models.Index(fields=['token_acceso']),
        ]
        unique_together = [['contrato', 'email']]

    def __str__(self):
        return f"{self.nombre_completo} - {self.contrato.titulo}"


class HistorialContrato(models.Model):
    """
    Modelo para auditoría completa de todas las acciones en el contrato
    """
    TIPO_ACCION_CHOICES = [
        ('creacion', 'Creación'),
        ('modificacion', 'Modificación'),
        ('activacion', 'Activación'),
        ('firma', 'Firma'),
        ('visualizacion', 'Visualización'),
        ('descarga', 'Descarga'),
        ('cancelacion', 'Cancelación'),
        ('completado', 'Completado'),
        ('envio_email', 'Envío de Email'),
        ('verificacion', 'Verificación de Código'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='historial')
    
    # Acción
    tipo_accion = models.CharField(max_length=20, choices=TIPO_ACCION_CHOICES)
    descripcion = models.TextField()
    
    # Usuario (puede ser None para acciones anónimas)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    firmante = models.ForeignKey(FirmanteContrato, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Datos adicionales (JSON)
    datos_adicionales = models.JSONField(default=dict, blank=True)
    
    # Información de sesión
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp
    fecha_accion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Historial de Contrato'
        verbose_name_plural = 'Historial de Contratos'
        ordering = ['-fecha_accion']
        indexes = [
            models.Index(fields=['contrato', '-fecha_accion']),
            models.Index(fields=['tipo_accion', '-fecha_accion']),
        ]

    def __str__(self):
        return f"{self.contrato.titulo} - {self.get_tipo_accion_display()} - {self.fecha_accion}"


class CertificadoFirma(models.Model):
    """
    Certificado de firma digital con timestamp y hash del documento
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='certificados')
    firmante = models.ForeignKey(FirmanteContrato, on_delete=models.CASCADE, related_name='certificados')
    
    # Datos del certificado
    hash_documento = models.CharField(max_length=64, help_text="Hash del documento en el momento de la firma")
    hash_firma = models.CharField(max_length=64, help_text="Hash de la firma aplicada")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Información de verificación
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Certificado generado (JSON con toda la información)
    certificado_json = models.JSONField(help_text="Certificado completo en formato JSON")
    
    # Hash del certificado completo
    hash_certificado = models.CharField(max_length=64, unique=True, help_text="Hash único del certificado para verificación")
    
    class Meta:
        verbose_name = 'Certificado de Firma'
        verbose_name_plural = 'Certificados de Firma'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['contrato', '-timestamp']),
            models.Index(fields=['hash_certificado']),
        ]

    def __str__(self):
        return f"Certificado - {self.firmante.nombre_completo} - {self.timestamp}"

    def save(self, *args, **kwargs):
        # Generar el certificado JSON si no existe
        if not self.certificado_json:
            self.certificado_json = {
                'contrato_id': str(self.contrato.id),
                'contrato_titulo': self.contrato.titulo,
                'firmante': {
                    'nombre': self.firmante.nombre_completo,
                    'email': self.firmante.email,
                    'dni': self.firmante.dni,
                },
                'timestamp': self.timestamp.isoformat() if self.timestamp else None,
                'hash_documento': self.hash_documento,
                'hash_firma': self.hash_firma,
                'ip_address': self.ip_address,
                'metadata': {
                    'team_id': str(self.contrato.team.id),
                    'created_by': str(self.contrato.creado_por.id) if self.contrato.creado_por else None,
                }
            }
        
        # Calcular hash del certificado
        if not self.hash_certificado:
            certificado_str = json.dumps(self.certificado_json, sort_keys=True)
            self.hash_certificado = hashlib.sha256(certificado_str.encode()).hexdigest()
        
        super().save(*args, **kwargs)

    def verificar_integridad(self):
        """Verifica la integridad del certificado"""
        certificado_str = json.dumps(self.certificado_json, sort_keys=True)
        hash_calculado = hashlib.sha256(certificado_str.encode()).hexdigest()
        return hash_calculado == self.hash_certificado