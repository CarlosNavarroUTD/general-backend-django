# apps/servicios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServicioViewSet, CampoPersonalizadoViewSet, upload_image

router = DefaultRouter()
router.register(r'servicios', ServicioViewSet, basename='servicio')
router.register(r'campos-personalizados', CampoPersonalizadoViewSet, basename='campo-personalizado')

urlpatterns = [
    path('', include(router.urls)),
    path('servicios/upload-imagen/', upload_image, name='upload-imagen'),
]