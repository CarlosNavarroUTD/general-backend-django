from rest_framework import serializers
from .models import Archivo, AccesoArchivo
from django.contrib.auth import get_user_model

User = get_user_model()


class ArchivoSerializer(serializers.ModelSerializer):
    subido_por_info = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        fields = [
            'id', 'team', 'nombre', 'descripcion',
            'archivo_url', 'archivo_key',
            'tipo_archivo', 'tamano', 'hash_sha256',
            'subido_por', 'subido_por_info',
            'fecha_subida', 'fecha_modificacion',
            'es_privado', 'requiere_autenticacion'
        ]
        read_only_fields = [
            'id', 'hash_sha256', 'tamano',
            'fecha_subida', 'fecha_modificacion', 'subido_por'
        ]

class ArchivoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    subido_por_nombre = serializers.CharField(source='subido_por.get_full_name', read_only=True)

    
    class Meta:
        model = Archivo
        fields = [
            'id', 'nombre', 'tipo_archivo', 'tamano', 'fecha_subida',
            'subido_por_nombre', 'es_privado',  'archivo_url'
        ]
    
    def get_url(self, obj):
        return obj.archivo_url


class ArchivoCreateSerializer(serializers.ModelSerializer):
    archivo_url = serializers.URLField(required=True)
    archivo_key = serializers.CharField(required=True)
    tamano = serializers.IntegerField(required=False)
    class Meta:
        model = Archivo
        fields = [
            'team', 'nombre', 'descripcion',
            'archivo_url', 'archivo_key', 'tamano', 
            'tipo_archivo', 'es_privado', 'requiere_autenticacion'
        ]

    def create(self, validated_data):
        validated_data['subido_por'] = self.context['request'].user
        return super().create(validated_data)
    
class AccesoArchivoSerializer(serializers.ModelSerializer):
    """Serializer para registrar accesos a archivos"""
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    archivo_nombre = serializers.CharField(source='archivo.nombre', read_only=True)
    
    class Meta:
        model = AccesoArchivo
        fields = [
            'id', 'archivo', 'archivo_nombre', 'usuario', 'usuario_email',
            'tipo_acceso', 'ip_address', 'user_agent', 'fecha_acceso'
        ]
        read_only_fields = ['id', 'fecha_acceso']


class AccesoArchivoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear registros de acceso"""
    
    class Meta:
        model = AccesoArchivo
        fields = ['archivo', 'tipo_acceso']

    def create(self, validated_data):
        request = self.context['request']
        
        # Obtener información de la sesión
        validated_data['usuario'] = request.user if request.user.is_authenticated else None
        validated_data['ip_address'] = self.get_client_ip(request)
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return super().create(validated_data)

    def get_client_ip(self, request):
        """Obtener la IP del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip