from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArchivoViewSet, AccesoArchivoViewSet

app_name = 'archivos'

router = DefaultRouter()
router.register(r'archivos', ArchivoViewSet, basename='archivo')
router.register(r'accesos', AccesoArchivoViewSet, basename='acceso-archivo')

urlpatterns = [
    path('', include(router.urls)),
]