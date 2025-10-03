# conversaciones/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Conversacion
from leads.models import Lead, Equipo
from leads.serializers import UserSerializer, EquipoSerializer

class LeadBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para lead en conversaciones"""
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    
    class Meta:
        model = Lead
        fields = ['id', 'nombre', 'plataforma', 'plataforma_display', 'plataforma_id', 'telefono', 'email']

class ConversacionListSerializer(serializers.ModelSerializer):
    """Serializer para lista de conversaciones"""
    lead = LeadBasicSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    asignado_a = UserSerializer(read_only=True)
    equipo_asignado = EquipoSerializer(read_only=True)
    
    # Campos calculados
    total_mensajes = serializers.ReadOnlyField()
    duracion_dias = serializers.SerializerMethodField()
    ultimo_mensaje_fecha = serializers.SerializerMethodField()
    ultimo_mensaje_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversacion
        fields = [
            'id', 'lead', 'estado', 'estado_display', 'asignado_a', 'equipo_asignado',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_cierre', 'satisfaccion_cliente',
            'total_mensajes', 'duracion_dias', 'ultimo_mensaje_fecha', 'ultimo_mensaje_preview'
        ]
    
    def get_duracion_dias(self, obj):
        duracion = obj.duracion_conversacion
        return duracion.days
    
    def get_ultimo_mensaje_fecha(self, obj):
        ultimo_mensaje = obj.ultimo_mensaje
        return ultimo_mensaje.fecha if ultimo_mensaje else None
    
    def get_ultimo_mensaje_preview(self, obj):
        ultimo_mensaje = obj.ultimo_mensaje
        if ultimo_mensaje:
            # Truncar el contenido a 100 caracteres
            contenido = ultimo_mensaje.contenido
            return contenido[:100] + '...' if len(contenido) > 100 else contenido
        return None

class ConversacionDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para una conversación específica"""
    lead = LeadBasicSerializer(read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    asignado_a = UserSerializer(read_only=True)
    equipo_asignado = EquipoSerializer(read_only=True)
    
    # Campos calculados y estadísticas
    total_mensajes = serializers.ReadOnlyField()
    duracion_conversacion_formatted = serializers.SerializerMethodField()
    tiempo_respuesta_promedio_formatted = serializers.SerializerMethodField()
    mensajes_recientes = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversacion
        fields = [
            'id', 'lead', 'estado', 'estado_display', 'asignado_a', 'equipo_asignado',
            'fecha_creacion', 'fecha_actualizacion', 'fecha_cierre', 
            'tiempo_respuesta_promedio', 'tiempo_respuesta_promedio_formatted',
            'satisfaccion_cliente', 'total_mensajes', 'duracion_conversacion_formatted',
            'mensajes_recientes'
        ]
    
    def get_duracion_conversacion_formatted(self, obj):
        duracion = obj.duracion_conversacion
        dias = duracion.days
        horas = duracion.seconds // 3600
        minutos = (duracion.seconds % 3600) // 60
        
        return {
            'dias': dias,
            'horas': horas,
            'minutos': minutos,
            'total_segundos': duracion.total_seconds()
        }
    
    def get_tiempo_respuesta_promedio_formatted(self, obj):
        if obj.tiempo_respuesta_promedio:
            total_segundos = obj.tiempo_respuesta_promedio.total_seconds()
            horas = int(total_segundos // 3600)
            minutos = int((total_segundos % 3600) // 60)
            segundos = int(total_segundos % 60)
            
            return {
                'horas': horas,
                'minutos': minutos,
                'segundos': segundos,
                'total_segundos': total_segundos
            }
        return None
    
    def get_mensajes_recientes(self, obj):
        # Importación lazy para evitar dependencias circulares
        from mensajes.serializers import MensajeSerializer
        mensajes = obj.mensajes.all()[:10]  # Últimos 10 mensajes
        return MensajeSerializer(mensajes, many=True).data

class ConversacionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar conversaciones"""
    
    class Meta:
        model = Conversacion
        fields = [
            'lead', 'estado', 'asignado_a', 'equipo_asignado', 'satisfaccion_cliente'
        ]
    
    def validate_satisfaccion_cliente(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("La satisfacción debe estar entre 1 y 5 estrellas")
        return value
    
    def validate_lead(self, value):
        # Verificar que el lead existe y está activo
        if not value:
            raise serializers.ValidationError("El lead es requerido")
        return value

class ConversacionStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de conversaciones"""
    total_conversaciones = serializers.IntegerField()
    conversaciones_abiertas = serializers.IntegerField()
    conversaciones_cerradas = serializers.IntegerField()
    conversaciones_en_seguimiento = serializers.IntegerField()
    
    # Métricas de tiempo
    tiempo_respuesta_promedio_global = serializers.DurationField()
    duracion_promedio_conversacion = serializers.DurationField()
    
    # Satisfacción
    satisfaccion_promedio = serializers.FloatField()
    total_con_satisfaccion = serializers.IntegerField()
    
    # Por usuario/equipo
    conversaciones_por_usuario = serializers.DictField()
    conversaciones_por_equipo = serializers.DictField()
    
    # Tendencias (últimos 30 días)
    conversaciones_diarias = serializers.ListField(
        child=serializers.DictField()
    )

class ConversacionCloseSerializer(serializers.Serializer):
    """Serializer para cerrar conversaciones"""
    satisfaccion_cliente = serializers.IntegerField(
        required=False, 
        min_value=1, 
        max_value=5,
        help_text="Calificación de satisfacción del cliente (1-5 estrellas)"
    )
    nota_cierre = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Nota opcional sobre el cierre de la conversación"
    )
    
    def validate(self, data):
        # Validaciones adicionales si es necesario
        return data

class ConversacionTransferSerializer(serializers.Serializer):
    """Serializer para transferir conversaciones"""
    nuevo_asignado = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    nuevo_equipo = serializers.PrimaryKeyRelatedField(
        queryset=Equipo.objects.all(),
        required=False,
        allow_null=True
    )
    motivo_transferencia = serializers.CharField(
        max_length=200,
        help_text="Motivo de la transferencia"
    )
    
    def validate(self, data):
        nuevo_asignado = data.get('nuevo_asignado')
        nuevo_equipo = data.get('nuevo_equipo')
        
        if not nuevo_asignado and not nuevo_equipo:
            raise serializers.ValidationError(
                "Debe especificar al menos un nuevo asignado (usuario o equipo)"
            )
        
        return data

# Serializer para reportes avanzados
class ConversacionReportSerializer(serializers.Serializer):
    """Serializer para reportes detallados de conversaciones"""
    periodo = serializers.CharField()
    total_conversaciones = serializers.IntegerField()
    tiempo_respuesta_promedio = serializers.DurationField()
    satisfaccion_promedio = serializers.FloatField()
    tasa_resolucion = serializers.FloatField()
    
    # Distribución por estado
    distribucion_estados = serializers.DictField()
    
    # Top performers
    mejores_agentes = serializers.ListField(
        child=serializers.DictField()
    )
    
    # Análisis temporal
    tendencia_volumen = serializers.ListField(
        child=serializers.DictField()
    )
    tendencia_satisfaccion = serializers.ListField(
        child=serializers.DictField()
    )