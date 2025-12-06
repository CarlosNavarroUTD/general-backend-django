# apps/usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.conf import settings

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El Email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('tipo_usuario', 'administrador')
        return self.create_user(email, password, **extra_fields)

class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True)
    nombre_usuario = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True, unique=True)  # 👈 Añadir este campo opcional

    tipo_usuario = models.CharField(max_length=20, choices=[
        ('administrador', 'Administrador'),
        ('usuario', 'Usuario'),
        ('invitado', 'Invitado'),
        ('cliente', 'Cliente'),
        ('proveedor', 'Proveedor'),
        ('empleado', 'Empleado'),
        ('doctor', 'Doctor'),
        ('paciente', 'Paciente'),
        ('miembro', 'Miembro'),
        ('arrendador', 'Arrendador'),
        ('otro', 'Otro'),
    ])
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre_usuario', 'tipo_usuario']

    class Meta:
        db_table = 'Usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

class Persona(models.Model):
    id_persona = models.AutoField(primary_key=True)
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='persona')
    nombre = models.CharField(max_length=255)
    apellido = models.CharField(max_length=255)

    class Meta:
        db_table = 'Persona'
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

class ActividadUsuario(models.Model):
    TIPO_ACTIVIDAD_CHOICES = [
        ('DOCUMENTO_SUBIDO', 'Documento Subido'),
        ('DOCUMENTO_ELIMINADO', 'Documento Eliminado'),
        ('CITA_AGENDADA', 'Cita Agendada'),
        ('CITA_CANCELADA', 'Cita Cancelada'),
        ('NOTA_AGREGADA', 'Nota Agregada'),
        ('OTRO', 'Otro'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='actividades'
    )
    tipo_actividad = models.CharField(
        max_length=50,
        choices=TIPO_ACTIVIDAD_CHOICES,
        default='OTRO'
    )
    descripcion = models.TextField()
    fecha_actividad = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_actividad']
        verbose_name = 'Actividad de Usuario'
        verbose_name_plural = 'Actividades de Usuario'
    
    def __str__(self):
        return f"{self.usuario.nombre} - {self.tipo_actividad} - {self.fecha_actividad}"


class DocumentoUsuario(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('IDENTIFICACION', 'Identificación'),
        ('HISTORIA_CLINICA', 'Historia Clínica'),
        ('RADIOGRAFIA', 'Radiografía'),
        ('LABORATORIO', 'Laboratorio'),
        ('RECETA', 'Receta'),
        ('CONSENTIMIENTO', 'Consentimiento'),
        ('OTRO', 'Otro'),
    ]
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documentos'
    )
    tipo_documento = models.CharField(
        max_length=50,
        choices=TIPO_DOCUMENTO_CHOICES,
        default='OTRO'
    )
    archivo = models.FileField(upload_to='documentos_usuarios/%Y/%m/')
    nombre_original = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_subida']
        verbose_name = 'Documento de Usuario'
        verbose_name_plural = 'Documentos de Usuario'
    
    def __str__(self):
        return f"{self.usuario.nombre} - {self.nombre_original or self.archivo.name}"
    
    def save(self, *args, **kwargs):
        if not self.nombre_original and self.archivo:
            self.nombre_original = self.archivo.name
        super().save(*args, **kwargs)