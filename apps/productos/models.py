from django.db import models
from apps.teams.models import Team


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
    
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='productos')
    
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES)
    
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    imagenes = models.JSONField(default=list, blank=True, help_text="URLs de imágenes del producto")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-creado_en']

    def __str__(self):
        return self.nombre

    @property
    def stock_total(self):
        return self.stock.cantidad if hasattr(self, "stock") else 0


class Stock(models.Model):
    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        related_name="stock"
    )
    cantidad = models.IntegerField(default=0)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"

    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"
