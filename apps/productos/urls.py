from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MarcaViewSet, ProductoViewSet, StockViewSet

app_name = 'productos'

router = DefaultRouter()
router.register(r'marcas', MarcaViewSet, basename='marca')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'stock', StockViewSet, basename='stock')

urlpatterns = [
    path('', include(router.urls)),
]