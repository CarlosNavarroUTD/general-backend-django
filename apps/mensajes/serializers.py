# mensajes/serializers.py
from rest_framework import serializers
from .models import Mensaje
from leads.models import Lead
from conversaciones.models import Conversacion

class LeadBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para lead en mensajes"""
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    
    class Meta:
        model = Lead
        fields = ['id', 'nombre', 'plataforma', 'plataforma_display', 'plataforma_id']

class ConversacionBasicSerializer(serializers.ModelSerializer):
    """Serializer básico para conversación en mensajes"""
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = Conversacion
        fields = ['id', 'estado', 'estado_display']

class MensajeListSerializer(serializers.ModelSerializer):
    """Serializer resumido para lista de mensajes"""
    lead = LeadBasicSerializer(read_only=True)
    conversacion = ConversacionBasicSerializer(read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    intencion_display = serializers.CharField(source='get_intencion_detectada_display', read_only=True)
    sentimiento_display = serializers.CharField(source='get_sentimiento_display', read_only=True)
    
    # Campos calculados
    preview_contenido = serializers.ReadOnlyField()
    tiempo_transcurrido = serializers.ReadOnlyField()
    
    class Meta:
        model = Mensaje
        fields = [
            'id', 'lead', 'conversacion', 'plataforma', 'plataforma_display',
            'tipo', 'tipo_display', 'preview_contenido', 'fecha', 'tiempo_transcurrido',
            'es_respuesta', 'respuesta_automatica', 'intencion_detectada', 'intencion_display',
            'sentimiento', 'sentimiento_display', 'confianza_nlp', 'procesado', 'requiere_atencion'
        ]

class MensajeDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para un mensaje específico"""
    lead = LeadBasicSerializer(read_only=True)
    conversacion = ConversacionBasicSerializer(read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    intencion_display = serializers.CharField(source='get_intencion_detectada_display', read_only=True)
    sentimiento_display = serializers.CharField(source='get_sentimiento_display', read_only=True)
    
    # Campos calculados
    tiempo_transcurrido = serializers.ReadOnlyField()
    longitud_contenido = serializers.SerializerMethodField()
    requiere_nlp = serializers.SerializerMethodField()
    
    class Meta:
        model = Mensaje
        fields = [
            'id', 'lead', 'conversacion', 'plataforma', 'plataforma_display',
            'tipo', 'tipo_display', 'contenido', 'fecha', 'tiempo_transcurrido',
            'es_respuesta', 'respuesta_automatica', 'intencion_detectada', 'intencion_display',
            'sentimiento', 'sentimiento_display', 'confianza_nlp', 'mensaje_original_id',
            'procesado', 'requiere_atencion', 'longitud_contenido', 'requiere_nlp'
        ]
    
    def get_longitud_contenido(self, obj):
        return len(obj.contenido)
    
    def get_requiere_nlp(self, obj):
        """Determina si el mensaje requiere análisis NLP"""
        return (
            not obj.procesado or 
            obj.intencion_detectada is None or 
            obj.sentimiento is None or
            obj.confianza_nlp is None or
            obj.confianza_nlp < 0.7
        )

class MensajeCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear mensajes"""
    
    class Meta:
        model = Mensaje
        fields = [
            'lead', 'conversacion', 'plataforma', 'tipo', 'contenido',
            'es_respuesta', 'respuesta_automatica', 'mensaje_original_id'
        ]
    
    def validate(self, data):
        lead = data.get('lead')
        conversacion = data.get('conversacion')
        
        # Si se especifica una conversación, debe pertenecer al lead
        if conversacion and conversacion.lead != lead:
            raise serializers.ValidationError(
                "La conversación debe pertenecer al lead especificado"
            )
        
        # Si no se especifica conversación, buscar una abierta o crearla
        if not conversacion and lead:
            conversacion_abierta = Conversacion.objects.filter(
                lead=lead, 
                estado='abierto'
            ).first()
            
            if conversacion_abierta:
                data['conversacion'] = conversacion_abierta
            # Si no hay conversación abierta, se creará en la vista
        
        return data

class MensajeUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar mensajes"""
    
    class Meta:
        model = Mensaje
        fields = [
            'contenido', 'tipo', 'intencion_detectada', 'sentimiento',
            'confianza_nlp', 'procesado', 'requiere_atencion'
        ]
    
    def validate_confianza_nlp(self, value):
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("La confianza NLP debe estar entre 0 y 1")
        return value

class MensajeNLPUpdateSerializer(serializers.ModelSerializer):
    """Serializer específico para actualizar análisis NLP"""
    
    class Meta:
        model = Mensaje
        fields = ['intencion_detectada', 'sentimiento', 'confianza_nlp', 'procesado']
    
    def validate_confianza_nlp(self, value):
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("La confianza NLP debe estar entre 0 y 1")
        return value
    
    def update(self, instance, validated_data):
        # Marcar como procesado automáticamente si se actualiza el NLP
        validated_data['procesado'] = True
        return super().update(instance, validated_data)

class MensajeStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de mensajes"""
    total_mensajes = serializers.IntegerField()
    mensajes_sin_procesar = serializers.IntegerField()
    mensajes_requieren_atencion = serializers.IntegerField()
    mensajes_respuesta = serializers.IntegerField()
    mensajes_automaticos = serializers.IntegerField()
    
    # Por tipo
    mensajes_por_tipo = serializers.DictField()
    
    # Por plataforma
    mensajes_por_plataforma = serializers.DictField()
    
    # Análisis NLP
    intenciones_detectadas = serializers.DictField()
    sentimientos_detectados = serializers.DictField()
    confianza_nlp_promedio = serializers.FloatField()
    
    # Tendencias temporales
    mensajes_por_hora = serializers.ListField(
        child=serializers.DictField()
    )
    mensajes_por_dia = serializers.ListField(
        child=serializers.DictField()
    )

class MensajeBulkActionSerializer(serializers.Serializer):
    """Serializer para acciones en lote sobre mensajes"""
    mensaje_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="Lista de IDs de mensajes"
    )
    accion = serializers.ChoiceField(
        choices=[
            ('marcar_procesado', 'Marcar como procesado'),
            ('marcar_atencion', 'Marcar requiere atención'),
            ('quitar_atencion', 'Quitar requiere atención'),
            ('asignar_intencion', 'Asignar intención'),
            ('asignar_sentimiento', 'Asignar sentimiento'),
        ]
    )
    
    # Campos opcionales según la acción
    intencion = serializers.ChoiceField(
        choices=Mensaje.INTENCIONES,
        required=False
    )
    sentimiento = serializers.ChoiceField(
        choices=Mensaje.SENTIMIENTOS,
        required=False
    )
    
    def validate(self, data):
        accion = data.get('accion')
        
        if accion == 'asignar_intencion' and not data.get('intencion'):
            raise serializers.ValidationError(
                "Se requiere especificar la intención para esta acción"
            )
        
        if accion == 'asignar_sentimiento' and not data.get('sentimiento'):
            raise serializers.ValidationError(
                "Se requiere especificar el sentimiento para esta acción"
            )
        
        return data

class MensajeSearchSerializer(serializers.Serializer):
    """Serializer para búsqueda avanzada de mensajes"""
    query = serializers.CharField(required=False, help_text="Texto a buscar en el contenido")
    lead_id = serializers.IntegerField(required=False)
    conversacion_id = serializers.IntegerField(required=False)
    plataforma = serializers.ChoiceField(choices=Lead.PLATAFORMAS, required=False)
    tipo = serializers.ChoiceField(choices=Mensaje.TIPOS, required=False)
    intencion = serializers.ChoiceField(choices=Mensaje.INTENCIONES, required=False)
    sentimiento = serializers.ChoiceField(choices=Mensaje.SENTIMIENTOS, required=False)
    es_respuesta = serializers.BooleanField(required=False)
    procesado = serializers.BooleanField(required=False)
    requiere_atencion = serializers.BooleanField(required=False)
    fecha_desde = serializers.DateTimeField(required=False)
    fecha_hasta = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        fecha_desde = data.get('fecha_desde')
        fecha_hasta = data.get('fecha_hasta')
        
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise serializers.ValidationError(
                "La fecha desde no puede ser mayor que la fecha hasta"
            )
        
        return data

# Serializers para análisis y reportes
class MensajeAnalysisSerializer(serializers.Serializer):
    """Serializer para análisis de mensajes"""
    periodo = serializers.CharField()
    total_mensajes = serializers.IntegerField()
    mensajes_procesados = serializers.IntegerField()
    tasa_procesamiento = serializers.FloatField()
    
    # Distribución por categorías
    distribucion_tipos = serializers.DictField()
    distribucion_intenciones = serializers.DictField()
    distribucion_sentimientos = serializers.DictField()
    distribucion_plataformas = serializers.DictField()
    
    # Métricas de calidad NLP
    confianza_promedio = serializers.FloatField()
    mensajes_baja_confianza = serializers.IntegerField()
    
    # Patrones temporales
    actividad_por_hora = serializers.ListField(
        child=serializers.DictField()
    )
    tendencia_volumenes = serializers.ListField(
        child=serializers.DictField()
    )

class MensajeConversationFlowSerializer(serializers.Serializer):
    """Serializer para análisis de flujo de conversación"""
    conversacion_id = serializers.IntegerField()
    total_mensajes = serializers.IntegerField()
    duracion_conversacion = serializers.DurationField()
    patron_respuesta = serializers.ListField(
        child=serializers.DictField()
    )
    cambios_sentimiento = serializers.ListField(
        child=serializers.DictField()
    )
    tiempo_respuesta_promedio = serializers.DurationField()
    efectividad_respuestas = serializers.FloatField()