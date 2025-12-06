# apps/citas/serializers.py
from rest_framework import serializers
from .models import Cita
from apps.usuarios.serializers import UsuarioSerializer
from apps.servicios.serializers import ServicioSerializer


class CitaSerializer(serializers.ModelSerializer):
    usuario_info = UsuarioSerializer(source='usuario', read_only=True)
    servicio_info = ServicioSerializer(source='servicio', read_only=True)

    class Meta:
        model = Cita
        fields = [
            'id',
            'usuario', 'usuario_info',
            'servicio', 'servicio_info',
            'fecha_inicio', 'fecha_fin',
            'estado', 'notas',
            'fecha_creacion',
            'team'
        ]
        read_only_fields = ['fecha_creacion', 'usuario', 'team']
    
class ChatProcessorSerializer(serializers.Serializer):
    """Serializer para procesar el chat de entrada"""
    chat = serializers.CharField(
        required=True,
        allow_blank=False,
        help_text="Texto del chat o conversación a procesar"
    )
    
    def validate_chat(self, value):
        """Validar que el chat no esté vacío después de strip"""
        if not value.strip():
            raise serializers.ValidationError("El chat no puede estar vacío")
        return value.strip()
