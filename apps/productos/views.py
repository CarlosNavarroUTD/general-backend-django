from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q, Avg
from django_filters.rest_framework import DjangoFilterBackend
from .models import Marca, Producto, Stock
from .serializers import (
    MarcaSerializer,
    ProductoListSerializer,
    ProductoDetailSerializer,
    ProductoCreateUpdateSerializer,
    StockSerializer,
    StockCreateUpdateSerializer
)


class MarcaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar marcas
    """
    queryset = Marca.objects.all()
    serializer_class = MarcaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'creado_en']
    
    @action(detail=True, methods=['get'])
    def productos(self, request, pk=None):
        """
        Obtener todos los productos de una marca
        """
        marca = self.get_object()
        productos = marca.productos.all()
        serializer = ProductoListSerializer(productos, many=True)
        return Response(serializer.data)


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar productos
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'marca', 'sitio', 'activo']
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'precio', 'creado_en']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Producto.objects.select_related('marca', 'sitio', 'team')
        
        # Filtrar por teams del usuario usando TeamMember
        user_teams = user.teams.values_list('team', flat=True)
        queryset = queryset.filter(team__id__in=user_teams)
        
        # Filtro por rango de precio
        precio_min = self.request.query_params.get('precio_min', None)
        precio_max = self.request.query_params.get('precio_max', None)
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        
        # Filtro por stock disponible
        con_stock = self.request.query_params.get('con_stock', None)
        if con_stock and con_stock.lower() == 'true':
            queryset = queryset.filter(
                stock_entries__cantidad__gt=0
            ).distinct()
        
        # Filtro por team slug
        team_slug = self.request.query_params.get('team_slug', None)
        if team_slug:
            queryset = queryset.filter(team__slug=team_slug)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        elif self.action == 'retrieve':
            return ProductoDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductoCreateUpdateSerializer
        return ProductoListSerializer
    
    @action(detail=True, methods=['get'])
    def stock(self, request, pk=None):
        """
        Obtener el stock de un producto en todas las tiendas
        """
        producto = self.get_object()
        stocks = producto.stock_entries.select_related('sucursal')
        serializer = StockSerializer(stocks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sin_stock(self, request):
        """
        Obtener productos sin stock en ninguna tienda
        """
        productos = self.get_queryset().filter(
            Q(stock_entries__isnull=True) | 
            Q(stock_entries__cantidad=0)
        ).distinct()
        
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """
        Obtener estadísticas de productos por categoría
        """
        estadisticas = self.get_queryset().values('categoria').annotate(
            total=Count('id'),
            precio_promedio=Avg('precio'),
            stock_total=Sum('stock_entries__cantidad')
        ).order_by('-total')
        
        return Response(estadisticas)
    
    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """
        Activar un producto
        """
        producto = self.get_object()
        producto.activo = True
        producto.save()
        serializer = self.get_serializer(producto)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """
        Desactivar un producto
        """
        producto = self.get_object()
        producto.activo = False
        producto.save()
        serializer = self.get_serializer(producto)
        return Response(serializer.data)


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar el stock de productos
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['producto', 'sucursal']
    ordering_fields = ['cantidad', 'actualizado_en']
    
    def get_queryset(self):
        user = self.request.user
        queryset = Stock.objects.select_related('producto', 'sucursal')
        
        # Filtrar por teams del usuario usando TeamMember
        user_teams = user.teams.values_list('team', flat=True)
        queryset = queryset.filter(producto__team__id__in=user_teams)
        
        # Filtro por stock bajo
        stock_bajo = self.request.query_params.get('stock_bajo', None)
        if stock_bajo:
            try:
                limite = int(stock_bajo)
                queryset = queryset.filter(cantidad__lte=limite)
            except ValueError:
                pass
        
        return queryset
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return StockCreateUpdateSerializer
        return StockSerializer
    
    @action(detail=False, methods=['get'])
    def bajo_stock(self, request):
        """
        Obtener productos con stock bajo (menos de 10 unidades)
        """
        limite = request.query_params.get('limite', 10)
        try:
            limite = int(limite)
        except ValueError:
            limite = 10
        
        stocks = self.get_queryset().filter(
            cantidad__lte=limite,
            cantidad__gt=0
        )
        
        serializer = self.get_serializer(stocks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def sin_stock(self, request):
        """
        Obtener productos sin stock
        """
        stocks = self.get_queryset().filter(cantidad=0)
        serializer = self.get_serializer(stocks, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ajustar(self, request, pk=None):
        """
        Ajustar el stock (sumar o restar)
        """
        stock = self.get_object()
        ajuste = request.data.get('ajuste', 0)
        
        try:
            ajuste = int(ajuste)
        except (ValueError, TypeError):
            return Response(
                {'error': 'El ajuste debe ser un número entero'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        nueva_cantidad = stock.cantidad + ajuste
        
        if nueva_cantidad < 0:
            return Response(
                {'error': 'El stock no puede ser negativo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        stock.cantidad = nueva_cantidad
        stock.save()
        
        serializer = self.get_serializer(stock)
        return Response(serializer.data)