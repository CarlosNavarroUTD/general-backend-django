# leads/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters import rest_framework as filters
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Lead, ActividadLead
from .serializers import (
    LeadListSerializer, LeadDetailSerializer, LeadCreateUpdateSerializer,
    ActividadLeadSerializer
)
from apps.teams.models import TeamMember

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
    usuario_asignado = filters.NumberFilter(field_name='usuario_asignado__id')
    fecha_desde = filters.DateFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_hasta = filters.DateFilter(field_name='fecha_creacion', lookup_expr='lte')
    sin_asignar = filters.BooleanFilter(method='filter_sin_asignar')
    
    class Meta:
        model = Lead
        fields = ['nombre', 'estado', 'plataforma', 'fuente', 'asignado_a', 'usuario_asignado']
    
    def filter_sin_asignar(self, queryset, name, value):
        if value:
            return queryset.filter(asignado_a__isnull=True)
        return queryset

class LeadViewSet(viewsets.ModelViewSet):
    """ViewSet completo para gestión de leads"""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filterset_class = LeadFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return LeadListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return LeadCreateUpdateSerializer
        return LeadDetailSerializer

    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team')

        user_teams = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        
        qs = Lead.objects.select_related('asignado_a', 'usuario_asignado')
        
        if team_id:
            return qs.filter(asignado_a_id=team_id, asignado_a_id__in=user_teams).order_by('-fecha_creacion')
        return qs.filter(asignado_a_id__in=user_teams).order_by('-fecha_creacion')

    def perform_create(self, serializer):
        lead = serializer.save()
        ActividadLead.objects.create(
            lead=lead,
            usuario=self.request.user,
            tipo='creacion',
            descripcion=f'Lead creado: {lead.nombre}'
        )

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas generales de leads del equipo"""
        team_id = request.query_params.get('team')
        if not team_id:
            return Response({"error": "Se requiere el parámetro 'team'."}, status=status.HTTP_400_BAD_REQUEST)

        leads = Lead.objects.filter(asignado_a_id=team_id)
        total = leads.count()
        
        stats = {
            'total': total,
            'nuevos': leads.filter(estado='nuevo').count(),
            'contactados': leads.filter(estado='contactado').count(),
            'en_seguimiento': leads.filter(estado='en_seguimiento').count(),
            'convertidos': leads.filter(estado='convertido').count(),
            'perdidos': leads.filter(estado='perdido').count(),
            'tasa_conversion': round(leads.filter(estado='convertido').count() / total * 100, 1) if total > 0 else 0,
            'valor_total_estimado': leads.aggregate(total=Sum('valor_estimado'))['total'] or 0,
        }
        return Response(stats)

    @action(detail=False, methods=['post'], url_path='public', permission_classes=[permissions.AllowAny])
    def public_create(self, request):
        """Crear lead desde formulario público (sin autenticación)"""
        serializer = LeadCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save()
            ActividadLead.objects.create(
                lead=lead,
                tipo='creacion',
                descripcion=f'Lead creado desde formulario público'
            )
            return Response(LeadListSerializer(lead).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
