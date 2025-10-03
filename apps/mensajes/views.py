# =============================
# mensajes/views.py (simple)
# =============================
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q

from .models import Mensaje
from .serializers import (
    MensajeListSerializer, MensajeDetailSerializer, MensajeCreateSerializer,
    MensajeUpdateSerializer, MensajeNLPUpdateSerializer
)
from apps.leads.models import Lead
from apps.conversaciones.models import Conversacion

class MensajeViewSet(viewsets.ModelViewSet):
    """
    ViewSet simple y funcional para Mensaje:
    - list, retrieve, create, update, partial_update, destroy
    - acciones: bulk_action, nlp_update (detail), stats (list)
    """
    queryset = Mensaje.objects.select_related('lead', 'conversacion').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lead', 'conversacion', 'plataforma', 'tipo', 'intencion_detectada', 'sentimiento', 'es_respuesta', 'procesado', 'requiere_atencion']
    search_fields = ['contenido', 'mensaje_original_id']
    ordering_fields = ['fecha', 'confianza_nlp']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MensajeListSerializer
        if self.action in ('retrieve',):
            return MensajeDetailSerializer
        if self.action in ('update', 'partial_update'):
            return MensajeUpdateSerializer
        if self.action == 'nlp_update':
            return MensajeNLPUpdateSerializer
        return MensajeCreateSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create: crea Mensaje y dispara procesamiento de flujo (preferible async con Celery).
        - Aquí se intenta usar una tarea Celery; si no existe, hace un fallback síncrono.
        """
        serializer = MensajeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mensaje = serializer.save()
        
        # Intentar disparar procesamiento de flujo en background (si tienes Celery)
        try:
            from apps.flows.tasks import process_message_flow_task
            process_message_flow_task.delay(mensaje.id)
        except Exception:
            # Fallback: llamada inline a función de servicio (no recomendado en producción)
            try:
                from apps.flows.services import process_incoming_message
                process_incoming_message(mensaje)
            except Exception:
                # no blockear la respuesta si el servicio de flows falla
                pass
        
        return Response(MensajeDetailSerializer(mensaje).data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Acción simple en lote. payload: { mensaje_ids: [...], accion: 'marcar_procesado'|'marcar_atencion'|... , intencion?, sentimiento? }
        """
        payload = request.data
        ids = payload.get('mensaje_ids', [])
        accion = payload.get('accion')
        if not ids or not accion:
            return Response({'detail': 'mensaje_ids y accion son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
        qs = Mensaje.objects.filter(id__in=ids)
        updated = 0
        if accion == 'marcar_procesado':
            updated = qs.update(procesado=True)
        elif accion == 'marcar_atencion':
            updated = qs.update(requiere_atencion=True)
        elif accion == 'quitar_atencion':
            updated = qs.update(requiere_atencion=False)
        elif accion == 'asignar_intencion':
            intencion = payload.get('intencion')
            if not intencion:
                return Response({'detail': 'intencion requerida para esta accion'}, status=400)
            updated = qs.update(intencion_detectada=intencion)
        elif accion == 'asignar_sentimiento':
            sentimiento = payload.get('sentimiento')
            if not sentimiento:
                return Response({'detail': 'sentimiento requerido para esta accion'}, status=400)
            updated = qs.update(sentimiento=sentimiento)
        else:
            return Response({'detail': 'accion desconocida'}, status=400)
        return Response({'updated': updated})
    
    @action(detail=True, methods=['post'])
    def nlp_update(self, request, pk=None):
        mensaje = self.get_object()
        serializer = MensajeNLPUpdateSerializer(mensaje, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MensajeDetailSerializer(mensaje).data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Estadísticas simples: total, sin procesar, requieren atención, automáticos, por tipo y plataforma.
        """
        total = Mensaje.objects.count()
        sin_procesar = Mensaje.objects.filter(procesado=False).count()
        requieren = Mensaje.objects.filter(requiere_atencion=True).count()
        automaticos = Mensaje.objects.filter(respuesta_automatica=True).count()
        por_tipo = dict(Mensaje.objects.values('tipo').annotate(count=Count('id')).values_list('tipo','count'))
        por_plataforma_qs = Mensaje.objects.values('plataforma').annotate(count=Count('id'))
        por_plataforma = {r['plataforma']: r['count'] for r in por_plataforma_qs}
        confianza_prom = Mensaje.objects.aggregate(avg=models.Avg('confianza_nlp'))['avg'] or 0.0
        return Response({
            'total_mensajes': total,
            'mensajes_sin_procesar': sin_procesar,
            'mensajes_requieren_atencion': requieren,
            'mensajes_automaticos': automaticos,
            'mensajes_por_tipo': por_tipo,
            'mensajes_por_plataforma': por_plataforma,
            'confianza_nlp_promedio': confianza_prom
        })


# ================================
# Endpoint webhook público (simple)
# ================================
@api_view(['POST'])
@permission_classes([AllowAny])
def incoming_webhook(request):
    """
    Endpoint público simple para recibir { sender: {...}, message: {...} }.
    - Crea Lead si no existe (básico), crea Mensaje y dispara procesamiento de flujo.
    - Recomendación: proteger mediante HMAC/token en producción.
    """
    payload = request.data
    sender = payload.get('sender')
    message = payload.get('message')
    if not sender or not message:
        return Response({'detail': 'sender y message son requeridos'}, status=400)
    # Buscar/crear Lead (adaptar según tu modelo)
    external_id = sender.get('id')
    plataforma = sender.get('type') or 'whatsapp'
    lead, _ = Lead.objects.get_or_create(plataforma_id=external_id, defaults={'plataforma': plataforma, 'nombre': sender.get('name')})
    # Obtener conversación abierta si existe
    conversacion = Conversacion.objects.filter(lead=lead, estado='abierto').first()
    mensaje = Mensaje.objects.create(
        lead=lead,
        conversacion=conversacion,
        plataforma=plataforma,
        tipo='mensaje_directo',
        direccion='in',
        contenido=message.get('text', '')[:10000],
        mensaje_original_id=message.get('id'),
        raw_payload=payload
    )
    # Disparar procesamiento de flows (preferible async)
    try:
        from apps.flows.tasks import process_message_flow_task
        process_message_flow_task.delay(mensaje.id)
    except Exception:
        try:
            from apps.flows.services import process_incoming_message
            process_incoming_message(mensaje)
        except Exception:
            pass
    return Response({'ok': True, 'mensaje_id': mensaje.id})

