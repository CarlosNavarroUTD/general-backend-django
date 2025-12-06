from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from .models import Tienda
from .serializers import (
    TiendaSerializer, 
    TiendaCreateSerializer, 
    TiendaDetailSerializer
)


class TiendaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tiendas
    
    list: Obtener lista de tiendas
    retrieve: Obtener detalle de una tienda
    create: Crear nueva tienda
    update: Actualizar tienda completa
    partial_update: Actualizar campos específicos
    destroy: Eliminar tienda
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Tienda.objects.select_related('team')
        
        # Filtrar por teams del usuario usando TeamMember
        user_teams = user.teams.values_list('team', flat=True)
        queryset = queryset.filter(team__id__in=user_teams)
        
        # Filtro por búsqueda
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(direccion__icontains=search) |
                Q(email__icontains=search)
            )
        
        # Filtro por team
        team_id = self.request.query_params.get('team', None)
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        
        # Filtro por slug del team
        team_slug = self.request.query_params.get('team_slug', None)
        if team_slug:
            queryset = queryset.filter(team__slug=team_slug)
        
        return queryset.annotate(
            productos_count=Count('productos', distinct=True),
            stock_count=Count('stock_entries', distinct=True)
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TiendaCreateSerializer
        elif self.action == 'retrieve':
            return TiendaDetailSerializer
        return TiendaSerializer
    
    def perform_create(self, serializer):
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas de una tienda específica
        """
        tienda = self.get_object()
        
        data = {
            'id': tienda.id,
            'nombre': tienda.nombre,
            'team': {
                'id': tienda.team.id,
                'name': tienda.team.name,
                'slug': tienda.team.slug
            },
            'total_productos': tienda.productos.count(),
            'total_stock_entries': tienda.stock_entries.count(),
            'productos_activos': tienda.productos.filter(activo=True).count(),
            'productos_inactivos': tienda.productos.filter(activo=False).count(),
            'stock_total': sum([s.cantidad for s in tienda.stock_entries.all()]),
        }
        
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def mis_tiendas(self, request):
        """
        Obtener tiendas de los equipos del usuario autenticado
        """
        user = request.user
        # Obtener los IDs de los teams del usuario a través de TeamMember
        user_teams = user.teams.values_list('team', flat=True)
        tiendas = self.get_queryset().filter(team__id__in=user_teams)
        serializer = self.get_serializer(tiendas, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_team(self, request):
        """
        Obtener tiendas agrupadas por team
        """
        user = request.user
        user_teams = user.teams.values_list('team', flat=True)
        
        from apps.teams.models import Team
        teams = Team.objects.filter(id__in=user_teams).prefetch_related('tiendas')
        
        data = []
        for team in teams:
            data.append({
                'team_id': team.id,
                'team_name': team.name,
                'team_slug': team.slug,
                'tiendas': TiendaSerializer(team.tiendas.all(), many=True).data
            })
        
        return Response(data)