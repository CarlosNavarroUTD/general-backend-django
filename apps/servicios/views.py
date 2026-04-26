# apps/servicios/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from django.core.files.storage import default_storage
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from .models import Servicio
from .serializers import (
    ServicioSerializer,
    ServicioPublicoSerializer,
)


# ──────────────────────────────────────────────
# Servicio
# ──────────────────────────────────────────────

class ServicioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar servicios.

    Endpoints principales:
        GET    /api/servicios/                              → lista servicios del team
        POST   /api/servicios/                              → crea servicio (con campos opcionales)
        GET    /api/servicios/{id}/                         → detalle
        PUT    /api/servicios/{id}/                         → actualización total
        PATCH  /api/servicios/{id}/                         → actualización parcial
        DELETE /api/servicios/{id}/                         → elimina
        GET    /api/servicios/publico/{team_slug}/          → endpoint público

    Ejemplo de body para crear con campos personalizados:
        {
            "nombre": "Corte clásico",
            "descripcion": "Servicio básico de corte",
            "precio": "150.00",
            "duracion": 45,
            "team": 1,
            "campos_input": [
                { "campo": 3, "valor": "Tijera" },
                { "campo": 5, "valor": 90 }
            ]
        }
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ServicioSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'precio', 'fecha_creacion']

    def get_queryset(self):
        user = self.request.user
        user_teams = user.teams.values_list('team', flat=True)
        queryset = Servicio.objects.select_related('team').filter(team__id__in=user_teams)

        # Filtros opcionales por query params
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)

        duracion_min = self.request.query_params.get('duracion_min')
        duracion_max = self.request.query_params.get('duracion_max')
        if duracion_min:
            queryset = queryset.filter(duracion__gte=duracion_min)
        if duracion_max:
            queryset = queryset.filter(duracion__lte=duracion_max)

        activo = self.request.query_params.get('activo')
        if activo is not None:
            queryset = queryset.filter(activo=activo.lower() == 'true')

        team_slug = self.request.query_params.get('team_slug')
        if team_slug:
            queryset = queryset.filter(team__slug=team_slug)

        return queryset

    def perform_create(self, serializer):
        if 'team' not in self.request.data:
            user_teams = self.request.user.teams.all()
            if user_teams.exists():
                serializer.save(team=user_teams.first().team)
            else:
                serializer.save()
        else:
            serializer.save()

    # ──────────────────────────────────────────
    # Endpoint público
    # ──────────────────────────────────────────

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='publico/(?P<team_slug>[^/.]+)'
    )
    def publico(self, request, team_slug=None):
        """
        Endpoint público para obtener servicios activos de un team.
        URL: GET /api/servicios/publico/{team_slug}/
        """
        servicios = Servicio.objects.filter(
            team__slug=team_slug,
            activo=True
        ).select_related('team')

        # Filtros opcionales
        precio_min = request.query_params.get('precio_min')
        precio_max = request.query_params.get('precio_max')
        if precio_min:
            servicios = servicios.filter(precio__gte=precio_min)
        if precio_max:
            servicios = servicios.filter(precio__lte=precio_max)

        duracion_min = request.query_params.get('duracion_min')
        duracion_max = request.query_params.get('duracion_max')
        if duracion_min:
            servicios = servicios.filter(duracion__gte=duracion_min)
        if duracion_max:
            servicios = servicios.filter(duracion__lte=duracion_max)

        search = request.query_params.get('search')
        if search:
            servicios = servicios.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )

        ordering = request.query_params.get('ordering', '-fecha_creacion')
        servicios = servicios.order_by(ordering)

        serializer = ServicioPublicoSerializer(servicios, many=True)
        return Response({
            'team_slug': team_slug,
            'total': servicios.count(),
            'servicios': serializer.data
        })


# ──────────────────────────────────────────────
# Upload de imagen
# ──────────────────────────────────────────────

@api_view(['POST'])
def upload_image(request):
    """
    Sube una imagen para un servicio.
    URL: POST /api/servicios/upload-imagen/
    """
    if 'image' not in request.FILES:
        return Response(
            {'error': 'No se envió ninguna imagen.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    image = request.FILES['image']
    filename = default_storage.save(f'servicios/{image.name}', image)
    url_img = request.build_absolute_uri(settings.MEDIA_URL + filename)

    return Response({'url_img': url_img}, status=status.HTTP_201_CREATED)