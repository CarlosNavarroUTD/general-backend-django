from django.db import models
from apps.teams.models import Team
from apps.tiendas.models import Tienda


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('ropa', 'Ropa'),
        ('electronica', 'Electrónica'),
        ('comida', 'Comida'),
        ('servicio', 'Servicios'),
        ('libros', 'Libros'),
        ('hogar', 'Hogar y decoración'),
        ('belleza', 'Belleza y cuidado personal'),
        ('mascotas', 'Productos para mascotas'),
        ('juguetes', 'Juguetes y entretenimiento'),
        ('otros', 'Otros'),
    ]
    
    sitio = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name='productos')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='productos')
    
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-creado_en']

    def __str__(self):
        return self.nombre

    @property
    def stock_total(self):
        """Retorna el stock total del producto en todas las tiendas"""
        return self.stock_entries.aggregate(models.Sum('cantidad'))['cantidad__sum'] or 0


class Stock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stock_entries")
    sucursal = models.ForeignKey(Tienda, on_delete=models.CASCADE, related_name="stock_entries", null=True, blank=True)
    cantidad = models.IntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stock"
        unique_together = [['producto', 'sucursal']]

    def __str__(self):
        sucursal_nombre = self.sucursal.nombre if self.sucursal else "Sin tienda"
        return f"{self.producto.nombre} - {sucursal_nombre} - {self.cantidad} unidades"