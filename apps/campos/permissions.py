# apps/campos/permissions.py

from rest_framework.permissions import BasePermission
from apps.teams.models import TeamMember


class EsMiembroDelTeam(BasePermission):
    """
    Valida que el usuario pertenezca al team indicado en:
      - query param ?team_id=   (GET, DELETE)
      - body { "team_id": ... } (POST, PUT, PATCH)
    """

    message = "No tienes permiso para operar en este team."

    def has_permission(self, request, view):
        team_id = (
            request.query_params.get('team_id')   # GET / DELETE
            or request.data.get('team_id')         # POST / PUT / PATCH
        )

        if not team_id:
            self.message = "Debes indicar el team_id."
            return False

        return TeamMember.objects.filter(
            team_id=team_id,
            user=request.user,
        ).exists()