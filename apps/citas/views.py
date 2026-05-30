# apps/citas/views.py
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Cita
from .serializers import CitaSerializer, ChatProcessorSerializer
from .services import ChatProcessor

class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.tipo_usuario == 'paciente':
            return Cita.objects.filter(paciente__usuario=user)
        
        team_id = self.request.query_params.get('team') or self.request.query_params.get('team_id')
        if team_id:
            from apps.teams.models import TeamMember
            if not TeamMember.objects.filter(user=user, team_id=team_id).exists():
                return Cita.objects.none()
            return Cita.objects.filter(team_id=team_id)
        
        # Fallback: all teams
        from apps.teams.models import TeamMember
        user_team_ids = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        return Cita.objects.filter(team_id__in=user_team_ids)

    def perform_create(self, serializer):
        user = self.request.user
        team_id = self.request.data.get('team') or self.request.data.get('team_id')
        
        from apps.teams.models import TeamMember
        if team_id:
            team_member = TeamMember.objects.filter(user=user, team_id=team_id).first()
        else:
            team_member = TeamMember.objects.filter(user=user).first()
            
        if not team_member:
            from rest_framework import serializers
            raise serializers.ValidationError("El usuario no pertenece a ningún equipo.")
        
        serializer.save(
            usuario=user,
            team=team_member.team
        )

    @action(detail=False, methods=['get'])
    def mis_citas(self, request):
        citas = Cita.objects.filter(paciente__usuario=request.user)
        serializer = self.get_serializer(citas, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        cita = self.get_object()
        cita.estado = 'cancelada'
        cita.save()
        return Response({'status': 'Cita cancelada'})


class ProcesarChatView(APIView):
    """
    Vista para procesar chat y extraer fechas/horarios.
    No requiere autenticación.
    
    POST /api/citas/procesar-chat/
    Body: {"chat": "texto del chat aquí"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Procesa el texto del chat y extrae eventos con fechas y horarios.
        
        Ejemplo de uso:
```
        POST /api/citas/procesar-chat/
        {
            "chat": "Hola, necesito una cita para el lunes 15\\nPerfecto, a las 3 pm\\nMejor el martes a la misma hora"
        }
```
        """
        # Validar entrada
        serializer = ChatProcessorSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Datos inválidos', 'detalles': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Procesar chat
        try:
            chat_texto = serializer.validated_data['chat']
            processor = ChatProcessor()
            resultado = processor.procesar_chat(chat_texto)
            
            return Response(resultado, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {
                    'error': 'Error al procesar el chat',
                    'detalle': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )