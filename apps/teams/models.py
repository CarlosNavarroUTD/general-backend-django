from django.db import models
from django.conf import settings
import string
import secrets

class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    # Límite máximo de usuarios por equipo (valor por defecto 10)
    max_users = models.PositiveIntegerField(default=10, help_text='Número máximo de usuarios que pueden pertenecer a este equipo')
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Solo generar el slug si no existe (al crear)
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)

    def generate_unique_slug(self):
        length = 12
        # Define los caracteres permitidos: a-z, A-Z, 0-9
        alphabet = string.ascii_letters + string.digits
        
        while True:
            # Generar string aleatorio
            slug = ''.join(secrets.choice(alphabet) for _ in range(length))
            # Verificar que no exista en la base de datos
            if not Team.objects.filter(slug=slug).exists():
                return slug

    def __str__(self):
        return self.name

class TeamMember(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrador'),
        ('MEMBER', 'Miembro'),
    )
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teams')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['team', 'user']
        
    def __str__(self):
        return f"{self.user} - {self.team} ({self.role})"

    def clean(self):
        """Enforce max_users limit on the related Team.
        Se llama automáticamente al validar el modelo (e.g. en admin o al usar serializers).
        """
        from django.core.exceptions import ValidationError
        if not self.pk:  # solo al crear
            current_members = TeamMember.objects.filter(team=self.team).count()
            if current_members >= self.team.max_users:
                raise ValidationError({
                    'team': f"El equipo '{self.team.name}' ya alcanzó el límite máximo de {self.team.max_users} usuarios."
                })

class Invitation(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pendiente'),
        ('ACCEPTED', 'Aceptada'),
        ('REJECTED', 'Rechazada'),
    )
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    def __str__(self):
        return f"Invitación a {self.email or self.phone} para {self.team}"