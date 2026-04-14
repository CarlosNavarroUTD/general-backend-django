from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PortafolioViewSet

router = DefaultRouter()
router.register(r'portafolio', PortafolioViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

