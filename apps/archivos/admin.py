from django.contrib import admin
from .models import Archivo, AccesoArchivo


@admin.register(Archivo)
class ArchivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'team', 'tipo_archivo', 'tamano', 'subido_por', 'fecha_subida', 'es_privado']
    list_filter = ['tipo_archivo', 'es_privado', 'fecha_subida', 'team']
    search_fields = ['nombre', 'descripcion', 'subido_por__email']
    readonly_fields = ['id', 'hash_sha256', 'tamano', 'fecha_subida', 'fecha_modificacion']
    date_hierarchy = 'fecha_subida'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'team', 'nombre', 'descripcion', 'archivo', 'tipo_archivo')
        }),
        ('Metadatos', {
            'fields': ('tamano', 'hash_sha256')
        }),
        ('Auditoría', {
            'fields': ('subido_por', 'fecha_subida', 'fecha_modificacion')
        }),
        ('Seguridad', {
            'fields': ('es_privado', 'requiere_autenticacion')
        }),
    )


@admin.register(AccesoArchivo)
class AccesoArchivoAdmin(admin.ModelAdmin):
    list_display = ['archivo', 'usuario', 'tipo_acceso', 'ip_address', 'fecha_acceso']
    list_filter = ['tipo_acceso', 'fecha_acceso']
    search_fields = ['archivo__nombre', 'usuario__email', 'ip_address']
    readonly_fields = ['id', 'fecha_acceso']
    date_hierarchy = 'fecha_acceso'
    
    fieldsets = (
        ('Información del Acceso', {
            'fields': ('id', 'archivo', 'usuario', 'tipo_acceso')
        }),
        ('Información de Sesión', {
            'fields': ('ip_address', 'user_agent', 'fecha_acceso')
        }),
    )