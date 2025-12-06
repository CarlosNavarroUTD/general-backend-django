from rest_framework import serializers
from .models import Tienda


class TiendaSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Tienda
        fields = [
            'id', 'nombre', 'direccion', 'telefono', 'email', 
            'horario', 'team', 'team_name', 'total_productos', 
            'creado_en', 'actualizado_en'
        ]
        read_only_fields = ['creado_en', 'actualizado_en']

    def get_total_productos(self, obj):
        return obj.productos.count()


class TiendaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tienda
        fields = [
            'nombre', 'direccion', 'telefono', 'email', 'horario', 'team'
        ]

    def validate_nombre(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres")
        return value


class TiendaDetailSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_slug = serializers.CharField(source='team.slug', read_only=True)
    productos_count = serializers.SerializerMethodField()
    stock_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tienda
        fields = [
            'id', 'nombre', 'direccion', 'telefono', 'email', 
            'horario', 'team', 'team_name', 'team_slug',
            'productos_count', 'stock_count',
            'creado_en', 'actualizado_en'
        ]

    def get_productos_count(self, obj):
        return obj.productos.count()

    def get_stock_count(self, obj):
        return obj.stock_entries.count()