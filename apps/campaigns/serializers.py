from rest_framework import serializers
from .models import Plantilla, Campana, CampanaLead
from apps.leads.serializers import LeadListSerializer
from apps.integraciones.serializers import WhatsappInstanceSerializer

class PlantillaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plantilla
        fields = ['id', 'nombre', 'team', 'contenido', 'creado_en', 'actualizado_en']

class CampanaLeadSerializer(serializers.ModelSerializer):
    lead_detalle = LeadListSerializer(source='lead', read_only=True)
    estado_envio_display = serializers.CharField(source='get_estado_envio_display', read_only=True)

    class Meta:
        model = CampanaLead
        fields = ['id', 'campana', 'lead', 'lead_detalle', 'estado_envio', 'estado_envio_display', 'mensaje_error', 'enviado_en']

class CampanaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    estadisticas = serializers.SerializerMethodField()
    plantilla_detalle = PlantillaSerializer(source='plantilla', read_only=True)
    whatsapp_instance_detalle = WhatsappInstanceSerializer(source='whatsapp_instance', read_only=True)

    class Meta:
        model = Campana
        fields = [
            'id', 'nombre', 'team', 'plantilla', 'plantilla_detalle', 
            'whatsapp_instance', 'whatsapp_instance_detalle', 'estado', 'estado_display', 
            'estadisticas', 'creado_en', 'actualizado_en'
        ]

    def get_estadisticas(self, obj):
        leads = obj.campana_leads.all()
        return {
            'total': leads.count(),
            'pendientes': leads.filter(estado_envio='pendiente').count(),
            'enviados': leads.filter(estado_envio='enviado').count(),
            'errores': leads.filter(estado_envio='error').count()
        }

class CampanaCreateSerializer(serializers.ModelSerializer):
    leads = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Campana
        fields = ['nombre', 'team', 'plantilla', 'whatsapp_instance', 'leads']

    def create(self, validated_data):
        leads_data = validated_data.pop('leads', [])
        campana = Campana.objects.create(**validated_data)
        
        # Crear los CampanaLead
        from apps.leads.models import Lead
        leads_qs = Lead.objects.filter(id__in=leads_data, asignado_a=campana.team)
        
        campana_leads = []
        for lead in leads_qs:
            campana_leads.append(CampanaLead(campana=campana, lead=lead))
        
        CampanaLead.objects.bulk_create(campana_leads)
        
        return campana
