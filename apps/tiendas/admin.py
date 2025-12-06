from django.contrib import admin
from .models import Tienda


@admin.register(Tienda)
class TiendaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'direccion', 'telefono', 'email', 'team', 'creado_en']
    list_filter = ['team', 'creado_en']
    search_fields = ['nombre', 'direccion', 'email', 'telefono', 'team__name']
    readonly_fields = ['creado_en', 'actualizado_en']
    autocomplete_fields = ['team']
    
    fieldsets = (
        ('Información básica', {
            'fields': ('nombre', 'team')
        }),
        ('Contacto', {
            'fields': ('direccion', 'telefono', 'email', 'horario')
        }),
        ('Metadata', {
            'fields': ('creado_en', 'actualizado_en'),
            'classes': ('collapse',)
        }),
    )