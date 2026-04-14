# views.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Portafolio
from .serializers import PortafolioSerializer

class PortafolioViewSet(viewsets.ModelViewSet):
    queryset = Portafolio.objects.all()
    serializer_class = PortafolioSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['giro', 'formato', 'team', 'disponible']
    search_fields = ['cliente', 'campana']
    ordering_fields = ['duracion', 'impactos', 'roi', 'engagement']

    # ============ ENDPOINT PÚBLICO ============
    @action(
        detail=False,
        methods=['get'],
        permission_classes=[AllowAny],
        url_path='publico/(?P<team_slug>[^/.]+)'
    )
    def publico(self, request, team_slug=None):
        """
        GET /api/portafolio/publico/{team_slug}/
        """

        if not team_slug:
            return Response(
                {'error': 'Se requiere el slug del team'},
                status=status.HTTP_400_BAD_REQUEST
            )

        portafolios = Portafolio.objects.filter(
            team__slug=team_slug,
            disponible=True
        ).select_related('team')

        # filtros opcionales
        giro = request.query_params.get('giro')
        if giro:
            portafolios = portafolios.filter(giro=giro)

        formato = request.query_params.get('formato')
        if formato:
            portafolios = portafolios.filter(formato=formato)

        roi_min = request.query_params.get('roi_min')
        roi_max = request.query_params.get('roi_max')

        if roi_min:
            portafolios = portafolios.filter(roi__gte=roi_min)
        if roi_max:
            portafolios = portafolios.filter(roi__lte=roi_max)

        # búsqueda
        search = request.query_params.get('search')
        if search:
            portafolios = portafolios.filter(
                Q(cliente__icontains=search) |
                Q(campana__icontains=search)
            )

        # ordenamiento
        ordering = request.query_params.get('ordering', '-id')
        portafolios = portafolios.order_by(ordering)

        serializer = PortafolioSerializer(portafolios, many=True)

        return Response({
            'team_slug': team_slug,
            'total': portafolios.count(),
            'resultados': serializer.data
        })