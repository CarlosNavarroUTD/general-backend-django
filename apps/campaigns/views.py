from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.teams.models import TeamMember
from .models import Plantilla, Campana, CampanaLead
from .serializers import PlantillaSerializer, CampanaSerializer, CampanaCreateSerializer
import threading
import requests
import time
from django.utils import timezone

# Mismas credenciales de Evolution API (deberían estar en settings o variables de entorno en producción)
EVOLUTION_API_URL = "http://evolution-api:8080"
EVOLUTION_API_KEY = "B3stS3cr3tAp1K3yEV0"

class PlantillaViewSet(viewsets.ModelViewSet):
    serializer_class = PlantillaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team')
        
        user_teams = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        if team_id:
            return Plantilla.objects.filter(team_id=team_id, team_id__in=user_teams)
        return Plantilla.objects.filter(team_id__in=user_teams)

class CampanaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CampanaCreateSerializer
        return CampanaSerializer

    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team')
        
        user_teams = TeamMember.objects.filter(user=user).values_list('team_id', flat=True)
        if team_id:
            return Campana.objects.filter(team_id=team_id, team_id__in=user_teams).order_by('-creado_en')
        return Campana.objects.filter(team_id__in=user_teams).order_by('-creado_en')

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        campana = self.get_object()
        
        if campana.estado in ['enviando', 'completado']:
            return Response({"error": "La campaña ya está en ejecución o completada."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not campana.whatsapp_instance:
            return Response({"error": "No hay instancia de WhatsApp seleccionada."}, status=status.HTTP_400_BAD_REQUEST)
        
        if not campana.plantilla:
            return Response({"error": "No hay plantilla seleccionada."}, status=status.HTTP_400_BAD_REQUEST)

        # Cambiar estado a enviando
        campana.estado = 'enviando'
        campana.save()

        # Iniciar hilo en background
        thread = threading.Thread(target=self._enviar_mensajes_background, args=(campana.id,))
        thread.start()

        return Response({"message": "Campaña iniciada en segundo plano."}, status=status.HTTP_200_OK)

    def _enviar_mensajes_background(self, campana_id):
        # Necesitamos volver a consultar la BD en este hilo
        campana = Campana.objects.get(id=campana_id)
        instance = campana.whatsapp_instance
        plantilla_texto = campana.plantilla.contenido

        headers = {
            "apikey": instance.token if instance.token else EVOLUTION_API_KEY,
            "Content-Type": "application/json"
        }

        url = f"{EVOLUTION_API_URL}/message/sendText/{instance.instance_id}"
        
        leads_pendientes = CampanaLead.objects.filter(campana=campana, estado_envio='pendiente')
        
        for cl in leads_pendientes:
            lead = cl.lead
            if not lead.telefono:
                cl.estado_envio = 'error'
                cl.mensaje_error = 'No tiene número de teléfono'
                cl.save()
                continue
            
            # Limpiar número de teléfono (quitar + y espacios)
            numero = lead.telefono.replace('+', '').replace(' ', '').replace('-', '')
            
            # Reemplazar variables básicas
            texto = plantilla_texto
            if '{{nombre}}' in texto:
                texto = texto.replace('{{nombre}}', lead.nombre or 'amigo')
            
            payload = {
                "number": numero,
                "text": texto
            }

            try:
                # Retardo para evitar baneos (1 segundo entre mensajes)
                time.sleep(1)
                
                response = requests.post(url, json=payload, headers=headers)
                
                if response.status_code in [200, 201]:
                    cl.estado_envio = 'enviado'
                    cl.enviado_en = timezone.now()
                else:
                    cl.estado_envio = 'error'
                    cl.mensaje_error = f"Status {response.status_code}: {response.text[:200]}"
                
            except Exception as e:
                cl.estado_envio = 'error'
                cl.mensaje_error = str(e)[:200]
            
            cl.save()

        # Actualizar estado final de la campaña
        campana.estado = 'completado'
        campana.save()
