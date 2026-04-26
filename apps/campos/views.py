# apps/campos/views.py

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Campo
from .serializers import CampoSerializer
from .permissions import EsMiembroDelTeam   # ← nuevo


class CampoViewSet(viewsets.ModelViewSet):
    serializer_class = CampoSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EsMiembroDelTeam,              # ← aplica a TODAS las acciones
    ]

    def _get_team_id(self):
        """Devuelve team_id desde query param o body (ya validado por el permiso)."""
        return (
            self.request.query_params.get('team_id')
            or self.request.data.get('team_id')
        )

    def get_queryset(self):
        # El permiso ya garantizó que team_id existe y el usuario pertenece al team
        return Campo.objects.filter(team_id=self._get_team_id())

    def perform_create(self, serializer):
        # No hace falta pasar team aquí; el serializer lo toma del campo team_id del body
        serializer.save()

    # ──────────────────────────────────────
    # Acción extra: listar campos por entidad
    # ──────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='entidades')
    def entidades(self, request):
        # EsMiembroDelTeam ya validó team_id y la membresía, sin duplicar lógica
        campos = (
            self.get_queryset()
                .filter(activo=True)
                .order_by('entidad', 'orden')
        )

        result = {}
        for campo in campos:
            result.setdefault(campo.entidad, []).append(
                CampoSerializer(campo, context={'request': request}).data
            )

        return Response(result)