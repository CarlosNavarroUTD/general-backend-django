# apps/servicios/views.py
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Servicio
from .serializers import ServicioSerializer

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.filter(activo=True)
    serializer_class = ServicioSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = Servicio.objects.all()
        if self.action == 'list' and not self.request.user.is_staff:
            queryset = queryset.filter(activo=True)
        return queryset
