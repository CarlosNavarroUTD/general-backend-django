# apps/servicios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServicioViewSet, upload_image

router = DefaultRouter()
router.register(r'servicios', ServicioViewSet, basename='servicio')

urlpatterns = [
    path('servicios/upload/', upload_image, name='upload-image'), 
    path('', include(router.urls)),  
]