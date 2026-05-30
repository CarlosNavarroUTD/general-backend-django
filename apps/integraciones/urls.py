# integraciones/urls.py

from django.urls import path
from .views import GoogleComentariosView, GooglePlaceBusinessViewSet, GoogleBusinessCommentsView, WhatsappInstanceViewSet, GoogleSheetIntegrationViewSet
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'google/businesses', GooglePlaceBusinessViewSet, basename='google-businesses')
router.register(r'whatsapp/instances', WhatsappInstanceViewSet, basename='whatsapp-instances')
router.register(r'googlesheets', GoogleSheetIntegrationViewSet, basename='googlesheets')

urlpatterns = [
    path('google/comentarios/', GoogleComentariosView.as_view(), name='google-comentarios'),
    path('auth/google/', views.google_auth_redirect, name='google_auth_redirect'),
    path('auth/google/callback/', views.GoogleAuthCallbackView.as_view(), name='google_auth_callback'),
    path('auth/google/status/', views.GoogleAuthStatusView.as_view(), name='google_auth_status'),
] + router.urls