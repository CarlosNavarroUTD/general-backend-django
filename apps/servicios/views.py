# apps/servicios/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.core.files.storage import default_storage
from django.conf import settings
from .models import Servicio
from .serializers import ServicioSerializer, ServicioPublicoSerializer


class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServicioSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'precio', 'fecha_creacion']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Servicio.objects.select_related('team')
        
        # Filtrar por teams del usuario usando TeamMember
        user_teams = user.teams.values_list('team', flat=True)
        queryset = queryset.filter(team__id__in=user_teams)
        
        # Filtro por rango de precio
        precio_min = self.request.query_params.get('precio_min', None)
        precio_max = self.request.query_params.get('precio_max', None)
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        
        # Filtro por duración
        duracion_min = self.request.query_params.get('duracion_min', None)
        duracion_max = self.request.query_params.get('duracion_max', None)
        
        if duracion_min:
            queryset = queryset.filter(duracion__gte=duracion_min)
        if duracion_max:
            queryset = queryset.filter(duracion__lte=duracion_max)
        
        # Filtro por activo
        activo = self.request.query_params.get('activo', None)
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == 'true')
        
        # Filtro por team slug
        team_slug = self.request.query_params.get('team_slug', None)
        if team_slug:
            queryset = queryset.filter(team__slug=team_slug)
        
        return queryset
    
    def perform_create(self, serializer):
        # Asignar el team del usuario automáticamente si no se especifica
        if 'team' not in self.request.data:
            # Obtener el primer team del usuario o usar el team por defecto
            user_teams = self.request.user.teams.all()
            if user_teams.exists():
                serializer.save(team=user_teams.first().team)
            else:
                serializer.save()
        else:
            serializer.save()
    
    # ============ ENDPOINT PÚBLICO ============
    @action(detail=False, methods=['get'], permission_classes=[AllowAny], url_path='publico/(?P<team_slug>[^/.]+)')
    def publico(self, request, team_slug=None):
        """
        Endpoint público para obtener servicios de un team específico
        URL: /api/servicios/publico/{team_slug}/
        """
        if not team_slug:
            return Response(
                {'error': 'Se requiere el slug del team'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener servicios activos del team
        servicios = Servicio.objects.filter(
            team__slug=team_slug,
            activo=True
        ).select_related('team')
        
        # Aplicar filtros opcionales
        precio_min = request.query_params.get('precio_min', None)
        precio_max = request.query_params.get('precio_max', None)
        
        if precio_min:
            servicios = servicios.filter(precio__gte=precio_min)
        if precio_max:
            servicios = servicios.filter(precio__lte=precio_max)
        
        # Filtro por duración
        duracion_min = request.query_params.get('duracion_min', None)
        duracion_max = request.query_params.get('duracion_max', None)
        
        if duracion_min:
            servicios = servicios.filter(duracion__gte=duracion_min)
        if duracion_max:
            servicios = servicios.filter(duracion__lte=duracion_max)
        
        # Búsqueda por texto
        search = request.query_params.get('search', None)
        if search:
            servicios = servicios.filter(
                Q(nombre__icontains=search) | 
                Q(descripcion__icontains=search)
            )
        
        # Ordenamiento
        ordering = request.query_params.get('ordering', '-fecha_creacion')
        servicios = servicios.order_by(ordering)
        
        serializer = ServicioPublicoSerializer(servicios, many=True)
        return Response({
            'team_slug': team_slug,
            'total': servicios.count(),
            'servicios': serializer.data
        })


@api_view(['POST'])
def upload_image(request):
    if 'image' not in request.FILES:
        return Response({'error': 'No se envió ninguna imagen'}, status=status.HTTP_400_BAD_REQUEST)
    
    image = request.FILES['image']
    filename = default_storage.save(f'servicios/{image.name}', image)
    url_img = request.build_absolute_uri(settings.MEDIA_URL + filename)
    
    return Response({'url_img': url_img}, status=status.HTTP_201_CREATED)