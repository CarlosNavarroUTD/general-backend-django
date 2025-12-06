from django.contrib import admin
from .models import (
    Contrato, CampoContrato, FirmanteContrato,
    HistorialContrato, CertificadoFirma
)


class CampoContratoInline(admin.TabularInline):
    model = CampoContrato
    extra = 0
    fields = ['nombre_campo', 'etiqueta', 'tipo_campo', 'pagina', 'posicion_x', 'posicion_y', 'requerido', 'orden']
    readonly_fields = ['firma_hash', 'firmado', 'fecha_firma']


class FirmanteContratoInline(admin.TabularInline):
    model = FirmanteContrato
    extra = 0
    fields = ['nombre_completo', 'email', 'estado', 'fecha_completado']
    readonly_fields = ['token_acceso', 'fecha_completado']


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'team', 'estado', 'fecha_creacion', 'fecha_expiracion', 'creado_por']
    list_filter = ['estado', 'fecha_creacion', 'team', 'requiere_autenticacion_doble']
    search_fields = ['titulo', 'descripcion', 'creado_por__email']
    readonly_fields = [
        'id', 'hash_documento_original', 'hash_documento_firmado',
        'token_formulario', 'token_visualizacion', 'fecha_creacion', 'fecha_completado'
    ]
    date_hierarchy = 'fecha_creacion'
    inlines = [CampoContratoInline, FirmanteContratoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id', 'team', 'titulo', 'descripcion', 'estado')
        }),
        ('Documentos', {
            'fields': ('documento_original', 'documento_firmado', 'hash_documento_original', 'hash_documento_firmado')
        }),
        ('Tokens de Acceso', {
            'fields': ('token_formulario', 'token_visualizacion'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_activacion', 'fecha_expiracion', 'fecha_completado')
        }),
        ('Auditoría', {
            'fields': ('creado_por',)
        }),
        ('Configuración de Seguridad', {
            'fields': ('requiere_autenticacion_doble', 'ip_permitidas', 'limite_intentos_firma')
        }),
        ('Notificaciones', {
            'fields': ('email_notificacion', 'notificar_cada_firma')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado != 'borrador':
            return self.readonly_fields + ['documento_original', 'team']
        return self.readonly_fields


@admin.register(CampoContrato)
class CampoContratoAdmin(admin.ModelAdmin):
    list_display = ['etiqueta', 'contrato', 'tipo_campo', 'pagina', 'firmado', 'fecha_firma']
    list_filter = ['tipo_campo', 'firmado', 'requerido', 'contrato__estado']
    search_fields = ['nombre_campo', 'etiqueta', 'contrato__titulo']
    readonly_fields = ['id', 'firma_hash', 'firmado', 'fecha_firma', 'ip_firma']
    
    fieldsets = (
        ('Información del Campo', {
            'fields': ('id', 'contrato', 'nombre_campo', 'etiqueta', 'tipo_campo')
        }),
        ('Posición en el PDF', {
            'fields': ('pagina', 'posicion_x', 'posicion_y', 'ancho', 'alto')
        }),
        ('Valor', {
            'fields': ('valor',)
        }),
        ('Firma Digital', {
            'fields': ('firma_imagen', 'firma_hash', 'firmado', 'fecha_firma', 'ip_firma'),
            'classes': ('collapse',)
        }),
        ('Validación', {
            'fields': ('requerido', 'validacion_regex', 'mensaje_ayuda', 'orden')
        }),
    )


@admin.register(FirmanteContrato)
class FirmanteContratoAdmin(admin.ModelAdmin):
    list_display = ['nombre_completo', 'email', 'contrato', 'estado', 'fecha_completado']
    list_filter = ['estado', 'fecha_creacion', 'fecha_completado']
    search_fields = ['nombre_completo', 'email', 'dni', 'contrato__titulo']
    readonly_fields = [
        'id', 'token_acceso', 'fecha_completado', 'fecha_creacion',
        'fecha_invitacion_enviada', 'ip_address', 'user_agent'
    ]
    date_hierarchy = 'fecha_creacion'
    
    fieldsets = (
        ('Información del Firmante', {
            'fields': ('id', 'contrato', 'nombre_completo', 'email', 'telefono', 'dni')
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_completado')
        }),
        ('Acceso', {
            'fields': ('token_acceso',),
            'classes': ('collapse',)
        }),
        ('Verificación', {
            'fields': ('codigo_verificacion', 'codigo_verificacion_expira', 'intentos_verificacion'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_invitacion_enviada', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Consentimiento', {
            'fields': ('acepta_terminos', 'fecha_aceptacion_terminos')
        }),
    )


@admin.register(HistorialContrato)
class HistorialContratoAdmin(admin.ModelAdmin):
    list_display = ['contrato', 'tipo_accion', 'usuario', 'firmante', 'fecha_accion']
    list_filter = ['tipo_accion', 'fecha_accion']
    search_fields = ['contrato__titulo', 'descripcion', 'usuario__email', 'firmante__nombre_completo']
    readonly_fields = ['id', 'fecha_accion']
    date_hierarchy = 'fecha_accion'
    
    fieldsets = (
        ('Información de la Acción', {
            'fields': ('id', 'contrato', 'tipo_accion', 'descripcion', 'datos_adicionales')
        }),
        ('Usuario', {
            'fields': ('usuario', 'firmante')
        }),
        ('Información de Sesión', {
            'fields': ('ip_address', 'user_agent', 'fecha_accion')
        }),
    )


@admin.register(CertificadoFirma)
class CertificadoFirmaAdmin(admin.ModelAdmin):
    list_display = ['contrato', 'firmante', 'timestamp', 'hash_certificado', 'verificar_integridad']
    list_filter = ['timestamp']
    search_fields = ['contrato__titulo', 'firmante__nombre_completo', 'hash_certificado']
    readonly_fields = ['id', 'hash_certificado', 'timestamp', 'verificar_integridad']
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Información del Certificado', {
            'fields': ('id', 'contrato', 'firmante', 'timestamp')
        }),
        ('Hashes', {
            'fields': ('hash_documento', 'hash_firma', 'hash_certificado')
        }),
        ('Información de Verificación', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Certificado JSON', {
            'fields': ('certificado_json',),
            'classes': ('collapse',)
        }),
    )
    
    def verificar_integridad(self, obj):
        return obj.verificar_integridad()
    verificar_integridad.boolean = True
    verificar_integridad.short_description = 'Integridad Verificada'