from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContratoViewSet, CampoContratoViewSet,
    HistorialContratoViewSet, CertificadoFirmaViewSet,
    formulario_contrato, ver_contrato, firmar_campo,
    solicitar_codigo_verificacion, verificar_codigo,
    descargar_certificado
)

app_name = 'contratos'

router = DefaultRouter()
router.register(r'contratos', ContratoViewSet, basename='contrato')
router.register(r'campos', CampoContratoViewSet, basename='campo-contrato')
router.register(r'historial', HistorialContratoViewSet, basename='historial-contrato')
router.register(r'certificados', CertificadoFirmaViewSet, basename='certificado-firma')

urlpatterns = [
    # Rutas del router (autenticadas)
    path('', include(router.urls)),
    
    # Rutas públicas (sin autenticación)
    path('formulario/<str:token>/', formulario_contrato, name='formulario-contrato'),
    path('ver/<str:token>/', ver_contrato, name='ver-contrato'),
    path('firmar/<str:token>/', firmar_campo, name='firmar-campo'),
    path('solicitar-codigo/<str:token>/', solicitar_codigo_verificacion, name='solicitar-codigo'),
    path('verificar-codigo/<str:token>/', verificar_codigo, name='verificar-codigo'),
    path('certificado/<str:hash_certificado>/', descargar_certificado, name='descargar-certificado'),
]