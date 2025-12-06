# apps/servicios/serializers.py
from rest_framework import serializers
from .models import Servicio

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = ['id', 'team', 'nombre', 'descripcion', 'precio', 'duracion', 'activo', 'fecha_creacion']
        read_only_fields = ['fecha_creacion']
