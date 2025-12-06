from django.contrib import admin
from .models import Conversacion, Message

@admin.register(Conversacion)
class ConversacionAdmin(admin.ModelAdmin):
    list_display = ['sender_id', 'team', 'status', 'platform', 'last_message_at']
    list_filter = ['status', 'platform', 'team']
    search_fields = ['sender_id']

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversacion', 'direction', 'type', 'created_at']
    list_filter = ['direction', 'type', 'created_at']