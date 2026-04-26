# apps/servicios/serializers.py
from rest_framework import serializers
from .models import Servicio
from apps.campos.serializers import CamposPersonalizadosMixin




# ──────────────────────────────────────────────
# Servicio — uso interno (autenticado)
# ──────────────────────────────────────────────

class ServicioSerializer(CamposPersonalizadosMixin, serializers.ModelSerializer):
    """
    Serializer completo para uso interno.

    - Lectura  → campos_valores: lista de valores existentes con detalle del campo.
    - Escritura → campos_input: lista de { campo, valor } para crear/reemplazar valores.
    """
    ENTIDAD = 'servicio'
    personalizados = serializers.JSONField(required=False, default=dict)

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
            'url_img',
            'personalizados',
        ]
        read_only_fields = ['fecha_creacion']



# ──────────────────────────────────────────────
# Servicio — endpoint público
# ──────────────────────────────────────────────

class ServicioPublicoSerializer(CamposPersonalizadosMixin, serializers.ModelSerializer):

    duracion_formateada = serializers.SerializerMethodField()
    personalizados = serializers.JSONField(required=False, default=dict)    
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
            'url_img',
            'personalizados',
        ]

    def get_duracion_formateada(self, obj):
        if obj.duracion is None:
            return None  # o "" o "Sin duración"
    
        if obj.duracion < 60:
            return f"{obj.duracion} min"
        
        horas = obj.duracion // 60
        minutos = obj.duracion % 60
        if minutos == 0:
            return f"{horas}h"
        return f"{horas}h {minutos}min"