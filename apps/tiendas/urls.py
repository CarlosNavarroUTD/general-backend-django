from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TiendaViewSet

app_name = 'tiendas'

router = DefaultRouter()
router.register(r'tiendas', TiendaViewSet, basename='tienda')

urlpatterns = [
    path('', include(router.urls)),
]