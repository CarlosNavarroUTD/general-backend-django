from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PlantillaViewSet, CampanaViewSet

router = DefaultRouter()
router.register(r'plantillas', PlantillaViewSet, basename='plantilla')
router.register(r'campanas', CampanaViewSet, basename='campana')

urlpatterns = [
    path('', include(router.urls)),
]
