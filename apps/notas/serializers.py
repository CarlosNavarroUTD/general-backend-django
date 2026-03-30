from rest_framework import serializers
from .models import Nota

class NotaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source='usuario.nombre_usuario',
        read_only=True
    )

    class Meta:
        model = Nota
        fields = [
            'id',
            'usuario',
            'usuario_nombre',
            'team',
            'servicio',
            'titulo',
            'contenido',
            'es_publica',
            'creada_en',
            'actualizada_en',
        ]
        read_only_fields = ['usuario']

    def create(self, validated_data):
        request = self.context['request']
        validated_data['usuario'] = request.user
        return super().create(validated_data)