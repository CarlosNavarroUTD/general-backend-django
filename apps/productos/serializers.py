from rest_framework import serializers
from .models import Marca, Producto, Stock


class MarcaSerializer(serializers.ModelSerializer):
    total_productos = serializers.SerializerMethodField()
    
    class Meta:
        model = Marca
        fields = ['id', 'nombre', 'descripcion', 'total_productos', 'creado_en']
        read_only_fields = ['creado_en']

    def get_total_productos(self, obj):
        return obj.productos.count()


class ProductoPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para endpoint público
    No expone información sensible del team
    """
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    stock_disponible = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 
            'nombre', 
            'descripcion', 
            'precio', 
            'categoria',
            'marca_nombre',
            'stock_disponible',
            'creado_en',
            'imagenes'
        ]
    
    def get_stock_disponible(self, obj):
        """
        Retorna True/False si hay stock, sin revelar cantidad exacta
        """
        return obj.stock_total > 0


class ProductoListSerializer(serializers.ModelSerializer):
    marca_nombre = serializers.CharField(source='marca.nombre', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    stock_total = serializers.ReadOnlyField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'marca_nombre',
            'team', 'team_name', 'stock_total', 'activo', 'creado_en', 'imagenes'
        ]


class ProductoDetailSerializer(serializers.ModelSerializer):
    marca = MarcaSerializer(read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_slug = serializers.CharField(source='team.slug', read_only=True)
    stock_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'team', 'team_name', 'team_slug',
            'stock_info', 'activo',
            'creado_en', 'actualizado_en', 'imagenes'
        ]

    def get_stock_info(self, obj):
        """
        Retorna información del stock del producto
        """
        # ✅ Verificar que el atributo existe antes de acceder
        if hasattr(obj, 'stock_entries') and obj.stock_entries.exists():
            stock = obj.stock_entries.first()
            return {
                'stock_id': stock.id,
                'cantidad': stock.cantidad,
                'actualizado_en': stock.actualizado_en
            }
        
        # ✅ Retornar valores por defecto si no hay stock
        return {
            'stock_id': None,
            'cantidad': 0,
            'actualizado_en': None
        }


class ProductoCreateUpdateSerializer(serializers.ModelSerializer):
    imagenes_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio', 'categoria',
            'marca', 'team', 'activo', 'imagenes_files'
        ]

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value

    def validate_nombre(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("El nombre debe tener al menos 3 caracteres")
        return value

    def create(self, validated_data):
        imagenes_files = validated_data.pop('imagenes_files', [])
        producto = super().create(validated_data)
        
        # Subir imágenes automáticamente
        if imagenes_files:
            from apps.archivos.models import Archivo
            urls_imagenes = []
            
            for imagen in imagenes_files:
                archivo = Archivo.objects.create(
                    team=producto.team,
                    nombre=imagen.name,
                    archivo=imagen,
                    tipo_archivo='imagen',
                    subido_por=self.context['request'].user
                )
                url = self.context['request'].build_absolute_uri(archivo.archivo.url)
                urls_imagenes.append(url)
            
            producto.imagenes = urls_imagenes
            producto.save()
        
        return producto


class StockSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_id = serializers.IntegerField(source='producto.id', read_only=True)
    team_name = serializers.CharField(source='producto.team.name', read_only=True)
    
    class Meta:
        model = Stock
        fields = [
            'id', 'producto', 'producto_id', 'producto_nombre', 
            'team_name', 'cantidad', 'actualizado_en'
        ]
        read_only_fields = ['actualizado_en']

    def validate_cantidad(self, value):
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value


class StockCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['producto', 'cantidad']

    def validate_cantidad(self, value):
        if value < 0:
            raise serializers.ValidationError("La cantidad no puede ser negativa")
        return value

    def validate_producto(self, value):
        """
        Validar que no exista ya un stock para este producto
        """
        if self.instance is None:  # Solo en creación
            if Stock.objects.filter(producto=value).exists():
                raise serializers.ValidationError(
                    "Ya existe un registro de stock para este producto"
                )
        return value