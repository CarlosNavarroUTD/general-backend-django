from rest_framework import serializers
from .models import Marca, Producto, Stock
from apps.tiendas.serializers import TiendaSerializer


class MarcaSerializer(serializers.ModelSerializer):
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'descripcion', 'total_productos', 'creado_en']
        read_only_fields = ['creado_en']

    def get_total_productos(self, obj):
        return obj.productos.count()


class ProductoListSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    sitio_nombre = serializers.CharField(source='sitio.nombre', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    stock_total = serializers.ReadOnlyField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'marca_nombre', 'sitio', 'sitio_nombre',
            'team', 'team_name', 'stock_total', 'activo', 'creado_en'
        ]


class ProductoDetailSerializer(serializers.ModelSerializer):
    marca = MarcaSerializer(read_only=True)
    sitio = TiendaSerializer(read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_slug = serializers.CharField(source='team.slug', read_only=True)
    stock_por_tienda = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'sitio', 'team', 'team_name', 'team_slug',
            'stock_por_tienda', 'activo',
            'creado_en', 'actualizado_en'
        ]

    def get_stock_por_tienda(self, obj):
        stocks = obj.stock_entries.select_related('sucursal')
        return [
            {
                'sucursal_id': stock.sucursal.id if stock.sucursal else None,
                'sucursal_nombre': stock.sucursal.nombre if stock.sucursal else 'Sin tienda',
                'cantidad': stock.cantidad,
                'actualizado_en': stock.actualizado_en
            }
            for stock in stocks
        ]


class ProductoCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'sitio', 'team', 'activo'
        ]

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value

    def validate_nombre(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres")
        return value


class StockSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    sucursal_nombre = serializers.CharField(source='sucursal.nombre', read_only=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'producto', 'producto_nombre', 'sucursal', 
            'sucursal_nombre', 'cantidad', 'actualizado_en'
        ]
        read_only_fields = ['actualizado_en']

    def validate_cantidad(self, value):
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value


class StockCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['producto', 'sucursal', 'cantidad']

    def validate(self, attrs):
        producto = attrs.get('producto')
        sucursal = attrs.get('sucursal')
        
        # Validar que la sucursal pertenezca al mismo team del producto
        if sucursal and producto and sucursal.team != producto.team:
            raise serializers.ValidationError(
                "La sucursal y el producto deben pertenecer al mismo equipo"
            )
        
        return attrs