from rest_framework import serializers
from .models import Archivo, AccesoArchivo
from django.contrib.auth import get_user_model

User = get_user_model()


class ArchivoSerializer(serializers.ModelSerializer):
    """Serializer principal para archivos"""
    subido_por_info = serializers.SerializerMethodField()
    url_archivo = serializers.SerializerMethodField()
    
    class Meta:
        model = Archivo
        fields = [
            'id', 'team', 'nombre', 'descripcion', 'archivo', 'url_archivo',
            'tipo_archivo', 'tamano', 'hash_sha256', 'subido_por',
            'subido_por_info', 'fecha_subida', 'fecha_modificacion',
            'es_privado', 'requiere_autenticacion'
        ]
        read_only_fields = ['id', 'hash_sha256', 'tamano', 'fecha_subida', 'fecha_modificacion', 'subido_por']

    def get_subido_por_info(self, obj):
        if obj.subido_por:
            return {
                'id': obj.subido_por.id,
                'email': obj.subido_por.email,
                'nombre': obj.subido_por.get_full_name() if hasattr(obj.subido_por, 'get_full_name') else obj.subido_por.email
            }
        return None

    def get_url_archivo(self, obj):
        request = self.context.get('request')
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        return None

    def validate_archivo(self, value):
        """Validar tamaño del archivo (máximo 50MB)"""
        if value.size > 50 * 1024 * 1024:  # 50MB
            raise serializers.ValidationError("El archivo no puede superar los 50MB.")
        return value


class ArchivoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    subido_por_nombre = serializers.CharField(source='subido_por.email', read_only=True)
    
    class Meta:
        model = Archivo
        fields = [
            'id', 'nombre', 'tipo_archivo', 'tamano', 'fecha_subida',
            'subido_por_nombre', 'es_privado'
        ]


class ArchivoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear archivos"""
    
    class Meta:
        model = Archivo
        fields = [
            'team', 'nombre', 'descripcion', 'archivo', 'tipo_archivo',
            'es_privado', 'requiere_autenticacion'
        ]

    def create(self, validated_data):
        # Asignar el usuario actual como quien sube el archivo
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