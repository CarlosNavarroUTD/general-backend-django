from django.contrib import admin
from .models import Marca, Producto, Stock


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'creado_en']
    search_fields = ['nombre', 'descripcion']
    readonly_fields = ['creado_en']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'precio', 'categoria', 'marca', 'team', 'activo', 'creado_en']
    list_filter = ['categoria', 'marca', 'activo', 'team', 'creado_en']
    search_fields = ['nombre', 'descripcion', 'team__name']
    readonly_fields = ['creado_en', 'actualizado_en']
    autocomplete_fields = ['team', 'marca']
    
    fieldsets = (
        ('Información básica', {
            'fields': ('nombre', 'descripcion', 'team')
        }),
        ('Detalles del producto', {
            'fields': ('precio', 'categoria', 'marca', 'activo')
        }),
        ('Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'cantidad', 'actualizado_en']
    list_filter = ['actualizado_en']
    search_fields = ['producto__nombre']
    readonly_fields = ['actualizado_en']
    autocomplete_fields = ['producto']