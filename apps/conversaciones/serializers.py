# apps/conversaciones/serializers.py
from rest_framework import serializers
from .models import Conversacion, Message

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'direction',
            'type',
            'content',
            'media_url',
            'metadata',
            'external_id',
            'sender_name',
            'sender_user',
            'created_at',
            'delivered_at',
            'read_at'
        ]
        read_only_fields = ['id', 'created_at']

class ConversacionListSerializer(serializers.ModelSerializer):
    """Serializer para listar conversaciones (sin mensajes)"""
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversacion
        fields = [
            'id',
            'sender_id',
            'lead',
            'status',
            'platform',
            'assigned_to',
            'created_at',
            'updated_at',
            'last_message_at',
            'last_message',
            'unread_count'
        ]
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'content': last_msg.content[:100],
                'type': last_msg.type,
                'direction': last_msg.direction,
                'created_at': last_msg.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        # Contar mensajes entrantes no leídos
        return obj.messages.filter(
            direction='INBOUND',
            read_at__isnull=True
        ).count()

class ConversacionDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de conversación con mensajes"""
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversacion
        fields = [
            'id',
            'sender_id',
            'lead',
            'status',
            'platform',
            'platform_data',
            'assigned_to',
            'created_at',
            'updated_at',
            'last_message_at',
            'messages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class CreateMessageSerializer(serializers.ModelSerializer):
    """Serializer para crear mensajes"""
    class Meta:
        model = Message
        fields = [
            'conversacion',
            'direction',
            'type',
            'content',
            'media_url',
            'metadata',
            'external_id',
            'sender_name'
        ]
    
    def create(self, validated_data):
        from django.utils import timezone
        message = Message.objects.create(**validated_data)
        
        # Actualizar last_message_at de la conversación
        conversacion = message.conversacion
        conversacion.last_message_at = timezone.now()
        conversacion.save(update_fields=['last_message_at', 'updated_at'])
        
        return message