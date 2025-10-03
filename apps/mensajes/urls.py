# ================================
# mensajes/urls.py
# ================================
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MensajeViewSet, incoming_webhook

router = DefaultRouter()
router.register(r'mensajes', MensajeViewSet, basename='mensaje')

urlpatterns = [
    path('', include(router.urls)),
    path('webhook/', incoming_webhook, name='mensajes-webhook'),
]
