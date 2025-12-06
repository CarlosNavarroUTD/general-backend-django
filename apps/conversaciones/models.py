# apps/conversaciones/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.teams.models import Team

User = get_user_model()

class MessageType(models.TextChoices):
    TEXT = "TEXT", "Texto"
    IMAGE = "IMAGE", "Imagen"
    AUDIO = "AUDIO", "Audio"
    VIDEO = "VIDEO", "Video"
    DOCUMENT = "DOCUMENT", "Documento"
    LOCATION = "LOCATION", "Ubicación"

class MessageDirection(models.TextChoices):
    INBOUND = "INBOUND", "Entrante"
    OUTBOUND = "OUTBOUND", "Saliente"

class ConversationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activa"
    CLOSED = "CLOSED", "Cerrada"
    ARCHIVED = "ARCHIVED", "Archivada"

class Conversacion(models.Model):
    """Conversación principal con un sender"""
    sender_id = models.CharField(max_length=150, db_index=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='conversaciones')
    lead = models.ForeignKey('leads.Lead', on_delete=models.SET_NULL, null=True, blank=True, related_name='conversaciones')
    
    # Estado
    status = models.CharField(max_length=20, choices=ConversationStatus.choices, default=ConversationStatus.ACTIVE)
    
    # Metadatos
    platform = models.CharField(max_length=50, blank=True, help_text="whatsapp, telegram, etc")
    platform_data = models.JSONField(blank=True, null=True)
    
    # Asignación
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_conversations')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conversaciones'
        unique_together = ('sender_id', 'team')
        ordering = ['-last_message_at', '-updated_at']
        indexes = [
            models.Index(fields=['sender_id', 'team']),
            models.Index(fields=['team', 'status']),
        ]

    def __str__(self):
        return f"Conversación {self.sender_id} - {self.team.name}"

class Message(models.Model):
    """Mensaje individual en una conversación"""
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='messages')
    
    # Dirección del mensaje
    direction = models.CharField(max_length=10, choices=MessageDirection.choices)
    
    # Contenido
    type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(blank=True, null=True, help_text="Datos adicionales del mensaje")
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID del mensaje en la plataforma externa")
    
    # Sender info
    sender_name = models.CharField(max_length=255, blank=True)
    sender_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_messages')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversacion', 'created_at']),
        ]

    def __str__(self):
        return f"{self.direction} - {self.type} - {self.created_at}"