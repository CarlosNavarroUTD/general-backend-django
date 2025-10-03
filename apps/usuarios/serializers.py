# backend/apps/usuarios/serializers.py

from rest_framework import serializers
from .models import Usuario, Persona



class PersonaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Persona
        fields = ['id_persona', 'nombre', 'apellido']


class UsuarioSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer(required=False, allow_null=True)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = ['id_usuario', 'nombre_usuario', 'email', 'tipo_usuario', 'phone', 'password', 'persona']
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
            persona = usuario.persona
            persona.nombre = persona_data.get('nombre', '')
            persona.apellido = persona_data.get('apellido', '')
            persona.save()


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
                persona = Persona.objects.create(usuario=instance, **persona_data)
        

        return instance
