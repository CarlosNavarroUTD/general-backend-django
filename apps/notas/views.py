from rest_framework import viewsets, permissions
from django.db import models
from .models import Nota
from .serializers import NotaSerializer

class NotaViewSet(viewsets.ModelViewSet):
    serializer_class = NotaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        return Nota.objects.filter(
            team__members__user=user 
        ).filter(
            activa=True
        ).filter(
            # privadas propias o públicas del team
            models.Q(usuario=user) | models.Q(es_publica=True)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)