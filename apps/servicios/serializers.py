# apps/servicios/serializers.py
from rest_framework import serializers
from .models import Servicio


class ServicioSerializer(serializers.ModelSerializer):
    """
    Serializer completo para uso interno (autenticado)
    """
    class Meta:
        model = Servicio
        fields = [
            'id', 
            'team', 
            'nombre', 
            'descripcion', 
            'precio', 
            'duracion', 
            'activo', 
            'fecha_creacion', 
            'url_img'
        ]
        read_only_fields = ['fecha_creacion']


class ServicioPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para endpoint público
    No expone información sensible del team
    """
    duracion_formateada = serializers.SerializerMethodField()
    
    class Meta:
        model = Servicio
        fields = [
            'id', 
            'nombre', 
            'descripcion', 
            'precio', 
            'duracion',
            'duracion_formateada',
            'fecha_creacion',
            'url_img'
        ]
    
    def get_duracion_formateada(self, obj):
        """
        Formatea la duración de minutos a un formato legible
        Ejemplo: 90 -> "1h 30min"
        """
        if obj.duracion < 60:
            return f"{obj.duracion} min"
        
        horas = obj.duracion // 60
        minutos = obj.duracion % 60
        
        if minutos == 0:
            return f"{horas}h"
        return f"{horas}h {minutos}min"