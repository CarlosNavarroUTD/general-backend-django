# apps/usuarios/serializers.py
from rest_framework import serializers
from .models import Usuario, Persona, ActividadUsuario, DocumentoUsuario

class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = ['id_persona', 'nombre', 'apellido']


class UsuarioSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer(required=False, allow_null=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'nombre_usuario', 'email', 
            'tipo_usuario', 'phone', 'password', 'persona'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'phone': {'required': False}
        }

    def create(self, validated_data):
        persona_data = validated_data.pop('persona', None)
        password = validated_data.pop('password')
        nombre_usuario = validated_data.pop('nombre_usuario', None)
        tipo_usuario = validated_data.pop('tipo_usuario', 'usuario')

        if not nombre_usuario:
            email = validated_data.get('email', '')
            nombre_usuario = email.split('@')[0] if '@' in email else email

        usuario = Usuario.objects.create_user(
            password=password,
            nombre_usuario=nombre_usuario,
            tipo_usuario=tipo_usuario,
            **validated_data
        )

        if persona_data:
            Persona.objects.create(usuario=usuario, **persona_data)

        return usuario

    def update(self, instance, validated_data):
        persona_data = validated_data.pop('persona', None)
        password = validated_data.pop('password', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if persona_data:
            persona = getattr(instance, 'persona', None)
            if persona:
                for attr, value in persona_data.items():
                    setattr(persona, attr, value)
                persona.save()
            else:
                Persona.objects.create(usuario=instance, **persona_data)

        return instance


class ActividadUsuarioSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source='usuario.nombre_usuario', 
        read_only=True
    )
    tipo_display = serializers.CharField(
        source='get_tipo_actividad_display', 
        read_only=True
    )
    
    class Meta:
        model = ActividadUsuario
        fields = [
            'id', 'usuario', 'usuario_nombre', 
            'tipo_actividad', 'tipo_display',
            'descripcion', 'fecha_actividad', 'created_at'
        ]
        read_only_fields = ['id', 'fecha_actividad', 'created_at']


class DocumentoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source='usuario.nombre_usuario', 
        read_only=True
    )
    tipo_display = serializers.CharField(
        source='get_tipo_documento_display', 
        read_only=True
    )
    archivo_url = serializers.SerializerMethodField()
    tamanio_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentoUsuario
        fields = [
            'id', 'usuario', 'usuario_nombre', 
            'nombre_original', 'tipo_documento', 'tipo_display',
            'archivo', 'archivo_url', 'tamanio_mb', 
            'descripcion', 'fecha_subida'
        ]
        read_only_fields = ['id', 'fecha_subida']
    
    def get_archivo_url(self, obj):
        request = self.context.get('request')
        if obj.archivo and request:
            return request.build_absolute_uri(obj.archivo.url)
        return None
    
    def get_tamanio_mb(self, obj):
        if obj.archivo:
            return round(obj.archivo.size / (1024 * 1024), 2)
        return 0