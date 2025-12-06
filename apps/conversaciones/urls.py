# apps/conversaciones/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversacionViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'conversaciones', ConversacionViewSet, basename='conversacion')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]

# Las URLs generadas serán:
# GET    /api/conversaciones/                     - Listar conversaciones
# POST   /api/conversaciones/                     - Crear conversación
# GET    /api/conversaciones/{id}/                - Detalle de conversación
# PUT    /api/conversaciones/{id}/                - Actualizar conversación
# DELETE /api/conversaciones/{id}/                - Eliminar conversación
# GET    /api/conversaciones/{id}/messages/       - Obtener mensajes de una conversación
# POST   /api/conversaciones/{id}/send_message/   - Enviar mensaje
# POST   /api/conversaciones/{id}/mark_as_read/   - Marcar como leído
# PATCH  /api/conversaciones/{id}/close/          - Cerrar conversación
# GET    /api/conversaciones/by_sender/?sender_id=XXX - Obtener por sender_id
# 
# GET    /api/messages/                           - Listar mensajes
# POST   /api/messages/                           - Crear mensaje
# GET    /api/messages/{id}/                      - Detalle de mensaje