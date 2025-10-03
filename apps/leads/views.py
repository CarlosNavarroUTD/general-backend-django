# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters
from django.db.models import Q, Count, Avg, Sum, Case, When, F
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Lead, Mensaje, Conversacion, Equipo, ActividadLead
from .serializers import (
    LeadSerializer, LeadCreateSerializer, LeadUpdateSerializer, LeadListSerializer,
    MensajeSerializer, MensajeCreateSerializer,
    ConversacionSerializer, ConversacionCreateSerializer,
    EquipoSerializer, EquipoCreateSerializer,
    ActividadLeadSerializer,
    EstadisticasLeadSerializer, EstadisticasEquipoSerializer
)

# Paginación personalizada
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Filtros
class LeadFilter(filters.FilterSet):
    """Filtros avanzados para leads"""
    nombre = filters.CharFilter(lookup_expr='icontains')
    estado = filters.MultipleChoiceFilter(choices=Lead.ESTADOS)
    plataforma = filters.MultipleChoiceFilter(choices=Lead.PLATAFORMAS)
    fuente = filters.MultipleChoiceFilter(choices=Lead.FUENTES)
    asignado_a = filters.NumberFilter(field_name='asignado_a__id')
    fecha_desde = filters.DateFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_hasta = filters.DateFilter(field_name='fecha_creacion', lookup_expr='lte')
    sin_asignar = filters.BooleanFilter(method='filter_sin_asignar')
    sin_respuesta = filters.BooleanFilter(method='filter_sin_respuesta')
    
    class Meta:
        model = Lead
        fields = ['nombre', 'estado', 'plataforma', 'fuente', 'asignado_a']
    
    def filter_sin_asignar(self, queryset, name, value):
        if value:
            return queryset.filter(asignado_a__isnull=True)
        return queryset
    
    def filter_sin_respuesta(self, queryset, name, value):
        if value:
            # Leads que no han recibido respuesta en las últimas 24 horas
            hace_24h = timezone.now() - timedelta(hours=24)
            return queryset.filter(
                ultima_interaccion__lt=hace_24h,
                estado__in=['nuevo', 'contactado']
            )
        return queryset

class MensajeFilter(filters.FilterSet):
    """Filtros para mensajes"""
    lead = filters.NumberFilter()
    conversacion = filters.NumberFilter()
    tipo = filters.MultipleChoiceFilter(choices=Mensaje.TIPOS)
    plataforma = filters.MultipleChoiceFilter(choices=Lead.PLATAFORMAS)
    fecha_desde = filters.DateTimeFilter(field_name='fecha', lookup_expr='gte')
    fecha_hasta = filters.DateTimeFilter(field_name='fecha', lookup_expr='lte')
    sin_procesar = filters.BooleanFilter(field_name='procesado', lookup_expr='exact', method='filter_sin_procesar')
    requiere_atencion = filters.BooleanFilter()
    
    class Meta:
        model = Mensaje
        fields = ['lead', 'conversacion', 'tipo', 'plataforma']
    
    def filter_sin_procesar(self, queryset, name, value):
        if value:
            return queryset.filter(procesado=False)
        return queryset

# ViewSets principales
class EquipoViewSet(viewsets.ModelViewSet):
    """ViewSet para equipos"""
    queryset = Equipo.objects.all()
    pagination_class = StandardResultsSetPagination
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EquipoCreateSerializer
        return EquipoSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action ==