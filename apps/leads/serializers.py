# leads/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Equipo, Lead, ActividadLead



class LeadListSerializer(serializers.ModelSerializer):
    """Serializer resumido para lista de leads"""
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    asignado_a_nombre = serializers.CharField(source='asignado_a.nombre', read_only=True)
    mensajes_count = serializers.ReadOnlyField()
    dias_desde_creacion = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = [
            'id', 'nombre', 'plataforma', 'plataforma_display', 'plataforma_id',
            'telefono', 'email', 'estado', 'estado_display', 'fuente', 'fuente_display',
            'asignado_a', 'asignado_a_nombre', 'fecha_creacion', 'ultima_interaccion',
            'valor_estimado', 'probabilidad_conversion', 'mensajes_count', 'dias_desde_creacion'
        ]
    
    def get_dias_desde_creacion(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.fecha_creacion
        return delta.days

class LeadDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para un lead específico"""
    plataforma_display = serializers.CharField(source='get_plataforma_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    fuente_display = serializers.CharField(source='get_fuente_display', read_only=True)
    asignado_a = EquipoSerializer(read_only=True)
    mensajes_count = serializers.ReadOnlyField()
    
    # Estadísticas adicionales
    tiempo_en_estado_actual = serializers.SerializerMethodField()
    actividades_recientes = serializers.SerializerMethodField()
    
    class Meta:
        model = Lead
        fields = [
            'id', 'nombre', 'plataforma', 'plataforma_display', 'plataforma_id',
            'telefono', 'email', 'estado', 'estado_display', 'fuente', 'fuente_display',
            'asignado_a', 'fecha_creacion', 'fecha_actualizacion', 'ultima_interaccion',
            'notas', 'valor_estimado', 'probabilidad_conversion', 'mensajes_count',
            'tiempo_en_estado_actual', 'actividades_recientes'
        ]
    
    def get_tiempo_en_estado_actual(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.fecha_actualizacion
        return {
            'dias': delta.days,
            'horas': delta.seconds // 3600,
            'minutos': (delta.seconds % 3600) // 60
        }
    
    def get_actividades_recientes(self, obj):
        actividades = obj.actividades.all()[:5]  # Últimas 5 actividades
        return ActividadLeadSerializer(actividades, many=True).data

class LeadCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar leads"""
    
    class Meta:
        model = Lead
        fields = [
            'nombre', 'plataforma', 'plataforma_id', 'telefono', 'email',
            'estado', 'fuente', 'asignado_a', 'notas', 'valor_estimado',
            'probabilidad_conversion'
        ]
    
    def validate_probabilidad_conversion(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La probabilidad debe estar entre 0 y 100")
        return value
    
    def validate(self, data):
        # Validar combinación única de plataforma y plataforma_id
        plataforma = data.get('plataforma')
        plataforma_id = data.get('plataforma_id')
        
        if plataforma and plataforma_id:
            queryset = Lead.objects.filter(
                plataforma=plataforma, 
                plataforma_id=plataforma_id
            )
            
            # Si estamos actualizando, excluir el objeto actual
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    "Ya existe un lead con esta combinación de plataforma y ID de plataforma"
                )
        
        return data

class ActividadLeadSerializer(serializers.ModelSerializer):
    """Serializer para actividades de lead"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()
    tiempo_transcurrido = serializers.SerializerMethodField()
    
    class Meta:
        model = ActividadLead
        fields = [
            'id', 'lead', 'usuario', 'usuario_nombre', 'tipo', 'tipo_display',
            'descripcion', 'fecha', 'tiempo_transcurrido'
        ]
        read_only_fields = ['lead', 'fecha']
    
    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return f"{obj.usuario.first_name} {obj.usuario.last_name}".strip() or obj.usuario.username
        return "Sistema"
    
    def get_tiempo_transcurrido(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.fecha
        
        if delta.days > 0:
            return f"hace {delta.days} día{'s' if delta.days != 1 else ''}"
        elif delta.seconds > 3600:
            horas = delta.seconds // 3600
            return f"hace {horas} hora{'s' if horas != 1 else ''}"
        elif delta.seconds > 60:
            minutos = delta.seconds // 60
            return f"hace {minutos} minuto{'s' if minutos != 1 else ''}"
        else:
            return "hace unos segundos"

# Serializers para estadísticas y reportes
class LeadStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de leads"""
    total_leads = serializers.IntegerField()
    leads_nuevos = serializers.IntegerField()
    leads_contactados = serializers.IntegerField()
    leads_en_seguimiento = serializers.IntegerField()
    leads_convertidos = serializers.IntegerField()
    leads_perdidos = serializers.IntegerField()
    tasa_conversion = serializers.FloatField()
    valor_total_estimado = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Por plataforma
    leads_por_plataforma = serializers.DictField()
    
    # Por equipo
    leads_por_equipo = serializers.DictField()