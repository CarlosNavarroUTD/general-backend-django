from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import FlowViewSet, NodeViewSet, PathViewSet, EntityViewSet

router = DefaultRouter()
router.register(r'flows', FlowViewSet, basename='flow')
router.register(r'nodes', NodeViewSet, basename='node')
router.register(r'paths', PathViewSet, basename='path')
router.register(r'entities', EntityViewSet, basename='entity')

urlpatterns = [
    path('', include(router.urls)),
]
