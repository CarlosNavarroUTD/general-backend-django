# apps/usuarios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, PersonaViewSet, DocumentoViewSet

# Creamos un enrutador para gestionar las URLs automáticamente
router = DefaultRouter()
router.register(r'users', UsuarioViewSet)
router.register(r'usuarios', UsuarioViewSet, basename='usuario-alt')
router.register(r'personas', PersonaViewSet)
router.register(r'documentos', DocumentoViewSet, basename='documento')


urlpatterns = [
    path('', include(router.urls)),  # Incluimos todas las rutas generadas por el router

]

