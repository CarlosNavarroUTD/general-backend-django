from rest_framework import serializers
from .models import (
    Contrato, CampoContrato, FirmanteContrato, 
    HistorialContrato, CertificadoFirma
)
from django.utils import timezone
from django.core.validators import EmailValidator
import re


class CampoContratoSerializer(serializers.ModelSerializer):
    """Serializer para campos del contrato"""
    
    class Meta:
        model = CampoContrato
        fields = [
            'id', 'contrato', 'nombre_campo', 'etiqueta', 'tipo_campo',
            'pagina', 'posicion_x', 'posicion_y', 'ancho', 'alto',
            'valor', 'firma_imagen', 'firma_hash', 'firmado', 'fecha_firma',
            'ip_firma', 'requerido', 'validacion_regex', 'mensaje_ayuda', 'orden'
        ]
        read_only_fields = ['id', 'firma_hash', 'firmado', 'fecha_firma', 'ip_firma']

    def validate_posicion_x(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("La posición X debe estar entre 0 y 100")
        return value

    def validate_posicion_y(self, value):
        if not 0 <= value <= 100:
            raise serializers.ValidationError("La posición Y debe estar entre 0 y 100")
        return value


class CampoContratoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear campos"""
    
    class Meta:
        model = CampoContrato
        fields = [
            'nombre_campo', 'etiqueta', 'tipo_campo', 'pagina',
            'posicion_x', 'posicion_y', 'ancho', 'alto',
            'requerido', 'validacion_regex', 'mensaje_ayuda', 'orden'
        ]


class CampoContratoUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar valores de campos"""
    
    class Meta:
        model = CampoContrato
        fields = ['valor']

    def validate_valor(self, value):
        campo = self.instance
        
        # Validar según el tipo de campo
        if campo.tipo_campo == 'email':
            validator = EmailValidator()
            validator(value)
        elif campo.tipo_campo == 'dni' and campo.validacion_regex:
            if not re.match(campo.validacion_regex, value):
                raise serializers.ValidationError("El DNI no tiene un formato válido")
        elif campo.tipo_campo == 'telefono':
            # Validación básica de teléfono
            if not re.match(r'^\+?[\d\s\-\(\)]+$', value):
                raise serializers.ValidationError("El teléfono no tiene un formato válido")
        
        return value


class FirmaSerializer(serializers.Serializer):
    """Serializer para procesar firmas"""
    firma_base64 = serializers.CharField()
    campo_id = serializers.UUIDField()

    def validate_firma_base64(self, value):
        """Validar que sea una imagen base64 válida"""
        if not value.startswith('data:image'):
            raise serializers.ValidationError("La firma debe ser una imagen en formato base64")
        return value


class FirmanteContratoSerializer(serializers.ModelSerializer):
    """Serializer para firmantes"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = FirmanteContrato
        fields = [
            'id', 'contrato', 'nombre_completo', 'email', 'telefono', 'dni',
            'estado', 'estado_display', 'fecha_completado', 'acepta_terminos',
            'fecha_aceptacion_terminos', 'fecha_creacion'
        ]
        read_only_fields = [
            'id', 'token_acceso', 'fecha_completado', 'fecha_aceptacion_terminos',
            'fecha_creacion'
        ]

    def validate_email(self, value):
        """Validar que el email no esté duplicado en el mismo contrato"""
        contrato = self.context.get('contrato')
        if contrato:
            if FirmanteContrato.objects.filter(contrato=contrato, email=value).exists():
                raise serializers.ValidationError("Este email ya está registrado para este contrato")
        return value


class FirmanteContratoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear firmantes"""
    
    class Meta:
        model = FirmanteContrato
        fields = ['nombre_completo', 'email', 'telefono', 'dni']


class ContratoSerializer(serializers.ModelSerializer):
    """Serializer principal para contratos"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    creado_por_info = serializers.SerializerMethodField()
    campos = CampoContratoSerializer(many=True, read_only=True)
    firmantes = FirmanteContratoSerializer(many=True, read_only=True)
    url_formulario = serializers.SerializerMethodField()
    url_visualizacion = serializers.SerializerMethodField()
    esta_expirado = serializers.SerializerMethodField()
    puede_firmar = serializers.SerializerMethodField()
    progreso_firmas = serializers.SerializerMethodField()
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'team', 'titulo', 'descripcion', 'documento_original',
            'documento_firmado', 'hash_documento_original', 'hash_documento_firmado',
            'estado', 'estado_display', 'fecha_creacion', 'fecha_activacion',
            'fecha_expiracion', 'fecha_completado', 'creado_por', 'creado_por_info',
            'requiere_autenticacion_doble', 'ip_permitidas', 'limite_intentos_firma',
            'email_notificacion', 'notificar_cada_firma', 'campos', 'firmantes',
            'url_formulario', 'url_visualizacion', 'esta_expirado', 'puede_firmar',
            'progreso_firmas'
        ]
        read_only_fields = [
            'id', 'hash_documento_original', 'hash_documento_firmado',
            'token_formulario', 'token_visualizacion', 'fecha_creacion',
            'fecha_completado', 'creado_por'
        ]

    def get_creado_por_info(self, obj):
        if obj.creado_por:
            return {
                'id': obj.creado_por.id,
                'email': obj.creado_por.email,
                'nombre': obj.creado_por.get_full_name() if hasattr(obj.creado_por, 'get_full_name') else obj.creado_por.email
            }
        return None

    def get_url_formulario(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/contratos/formulario/{obj.token_formulario}/')
        return None

    def get_url_visualizacion(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(f'/api/contratos/ver/{obj.token_visualizacion}/')
        return None

    def get_esta_expirado(self, obj):
        return obj.esta_expirado()

    def get_puede_firmar(self, obj):
        return obj.puede_firmar()

    def get_progreso_firmas(self, obj):
        """Calcular el progreso de firmas"""
        total_firmas = obj.campos.filter(tipo_campo='firma').count()
        firmas_completadas = obj.campos.filter(tipo_campo='firma', firmado=True).count()
        
        return {
            'total': total_firmas,
            'completadas': firmas_completadas,
            'porcentaje': (firmas_completadas / total_firmas * 100) if total_firmas > 0 else 0
        }


class ContratoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    creado_por_email = serializers.CharField(source='creado_por.email', read_only=True)
    total_firmantes = serializers.SerializerMethodField()
    firmantes_completados = serializers.SerializerMethodField()
    
    class Meta:
        model = Contrato
        fields = [
            'id', 'titulo', 'estado', 'estado_display', 'fecha_creacion',
            'fecha_expiracion', 'creado_por_email', 'total_firmantes',
            'firmantes_completados'
        ]

    def get_total_firmantes(self, obj):
        return obj.firmantes.count()

    def get_firmantes_completados(self, obj):
        return obj.firmantes.filter(estado='completado').count()


class ContratoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear contratos"""
    campos = CampoContratoCreateSerializer(many=True, required=False)
    
    class Meta:
        model = Contrato
        fields = [
            'team', 'titulo', 'descripcion', 'documento_original',
            'fecha_expiracion', 'requiere_autenticacion_doble',
            'ip_permitidas', 'limite_intentos_firma',
            'email_notificacion', 'notificar_cada_firma', 'campos'
        ]

    def create(self, validated_data):
        campos_data = validated_data.pop('campos', [])
        
        # Asignar el usuario actual como creador
        validated_data['creado_por'] = self.context['request'].user
        
        # Crear el contrato
        contrato = Contrato.objects.create(**validated_data)
        
        # Crear los campos
        for campo_data in campos_data:
            CampoContrato.objects.create(contrato=contrato, **campo_data)
        
        return contrato


class HistorialContratoSerializer(serializers.ModelSerializer):
    """Serializer para el historial de contratos"""
    tipo_accion_display = serializers.CharField(source='get_tipo_accion_display', read_only=True)
    usuario_email = serializers.CharField(source='usuario.email', read_only=True)
    firmante_nombre = serializers.CharField(source='firmante.nombre_completo', read_only=True)
    
    class Meta:
        model = HistorialContrato
        fields = [
            'id', 'contrato', 'tipo_accion', 'tipo_accion_display',
            'descripcion', 'usuario', 'usuario_email', 'firmante',
            'firmante_nombre', 'datos_adicionales', 'ip_address',
            'user_agent', 'fecha_accion'
        ]
        read_only_fields = ['id', 'fecha_accion']


class CertificadoFirmaSerializer(serializers.ModelSerializer):
    """Serializer para certificados de firma"""
    firmante_info = serializers.SerializerMethodField()
    contrato_info = serializers.SerializerMethodField()
    es_valido = serializers.SerializerMethodField()
    
    class Meta:
        model = CertificadoFirma
        fields = [
            'id', 'contrato', 'contrato_info', 'firmante', 'firmante_info',
            'hash_documento', 'hash_firma', 'timestamp', 'ip_address',
            'certificado_json', 'hash_certificado', 'es_valido'
        ]
        read_only_fields = ['id', 'timestamp', 'hash_certificado']

    def get_firmante_info(self, obj):
        return {
            'nombre': obj.firmante.nombre_completo,
            'email': obj.firmante.email,
            'dni': obj.firmante.dni
        }

    def get_contrato_info(self, obj):
        return {
            'titulo': obj.contrato.titulo,
            'fecha_creacion': obj.contrato.fecha_creacion
        }

    def get_es_valido(self, obj):
        return obj.verificar_integridad()


class VerificarCertificadoSerializer(serializers.Serializer):
    """Serializer para verificar un certificado"""
    hash_certificado = serializers.CharField(max_length=64)

    def validate_hash_certificado(self, value):
        """Validar que el hash tenga el formato correcto"""
        if not re.match(r'^[a-f0-9]{64}$', value):
            raise serializers.ValidationError("Hash de certificado inválido")
        return value


class FormularioDatosSerializer(serializers.Serializer):
    """Serializer para el formulario de datos del contrato"""
    datos = serializers.DictField(child=serializers.CharField())

    def validate_datos(self, value):
        """Validar que todos los campos requeridos estén presentes"""
        contrato = self.context.get('contrato')
        if not contrato:
            raise serializers.ValidationError("Contrato no encontrado")
        
        # Obtener campos requeridos
        campos_requeridos = contrato.campos.filter(requerido=True).exclude(tipo_campo='firma')
        
        for campo in campos_requeridos:
            if campo.nombre_campo not in value:
                raise serializers.ValidationError(f"El campo '{campo.etiqueta}' es requerido")
        
        return value