from rest_framework import viewsets, permissions
from django.db import models
from .models import Nota
from .serializers import NotaSerializer

class NotaViewSet(viewsets.ModelViewSet):
    serializer_class = NotaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team') or self.request.query_params.get('team_id')

        queryset = Nota.objects.filter(activa=True).filter(
            # privadas propias o públicas del team
            models.Q(usuario=user) | models.Q(es_publica=True)
        )

        if team_id:
            from apps.teams.models import TeamMember
            if not TeamMember.objects.filter(user=user, team_id=team_id).exists():
                return Nota.objects.none()
            return queryset.filter(team_id=team_id).distinct()
        
        # Fallback: all teams
        return queryset.filter(team__members__user=user).distinct()

    def perform_create(self, serializer):
        team_id = self.request.data.get('team')
        if team_id:
            from apps.teams.models import TeamMember
            if not TeamMember.objects.filter(user=self.request.user, team_id=team_id).exists():
                from rest_framework import exceptions
                raise exceptions.PermissionDenied("No tienes permisos en este equipo")
            serializer.save(usuario=self.request.user)
        else:
            # Fallback
            from apps.teams.models import TeamMember
            team_member = TeamMember.objects.filter(user=self.request.user).first()
            if team_member:
                serializer.save(usuario=self.request.user, team=team_member.team)
            else:
                serializer.save(usuario=self.request.user)