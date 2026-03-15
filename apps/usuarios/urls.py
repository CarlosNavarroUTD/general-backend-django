# apps/usuarios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, PersonaViewSet

router = DefaultRouter()
router.register(r'users', UsuarioViewSet)
router.register(r'usuarios', UsuarioViewSet, basename='usuario-alt')
router.register(r'personas', PersonaViewSet)


urlpatterns = [
    path('', include(router.urls)), 

]

