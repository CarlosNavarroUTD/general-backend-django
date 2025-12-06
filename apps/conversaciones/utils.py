# apps/conversaciones/utils.py
from django.utils import timezone
from .models import Conversacion, Message

def get_or_create_conversation(sender_id, team, platform='', lead=None):
    """
    Obtiene o crea una conversación para un sender
    """
    conversacion, created = Conversacion.objects.get_or_create(
        sender_id=sender_id,
        team=team,
        defaults={
            'platform': platform,
            'lead': lead,
            'status': 'ACTIVE'
        }
    )
    return conversacion, created

def add_message_to_conversation(
    conversacion,
    content,
    direction='INBOUND',
    message_type='TEXT',
    media_url=None,
    metadata=None,
    external_id=None,
    sender_name='',
    sender_user=None
):
    """
    Agrega un mensaje a una conversación y actualiza timestamps
    """
    message = Message.objects.create(
        conversacion=conversacion,
        direction=direction,
        type=message_type,
        content=content,
        media_url=media_url,
        metadata=metadata,
        external_id=external_id,
        sender_name=sender_name,
        sender_user=sender_user
    )
    
    # Actualizar last_message_at
    conversacion.last_message_at = timezone.now()
    conversacion.save(update_fields=['last_message_at', 'updated_at'])
    
    return message

def get_conversation_history(sender_id, team, limit=None):
    """
    Obtiene el historial completo de conversación de un sender
    """
    try:
        conversacion = Conversacion.objects.get(
            sender_id=sender_id,
            team=team
        )
        messages = conversacion.messages.all().order_by('created_at')
        
        if limit:
            messages = messages[:limit]
        
        return messages
    except Conversacion.DoesNotExist:
        return []

def create_inbound_message(sender_id, team, content, platform='', **kwargs):
    """
    Crea un mensaje entrante (del usuario hacia el sistema)
    Crea la conversación si no existe
    """
    conversacion, _ = get_or_create_conversation(
        sender_id=sender_id,
        team=team,
        platform=platform
    )
    
    return add_message_to_conversation(
        conversacion=conversacion,
        content=content,
        direction='INBOUND',
        **kwargs
    )

def create_outbound_message(sender_id, team, content, sender_user=None, **kwargs):
    """
    Crea un mensaje saliente (del sistema hacia el usuario)
    """
    conversacion, _ = get_or_create_conversation(
        sender_id=sender_id,
        team=team
    )
    
    return add_message_to_conversation(
        conversacion=conversacion,
        content=content,
        direction='OUTBOUND',
        sender_user=sender_user,
        **kwargs
    )