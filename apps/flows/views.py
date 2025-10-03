from rest_framework import viewsets
from .models import Flow, Node, Path, Entity, EntityValue, ConversationSession
from .serializers import FlowSerializer, NodeSerializer, PathSerializer, EntitySerializer
from rest_framework.permissions import IsAuthenticated
import random
import string
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from apps.teams.models import Team
from apps.leads.models import Lead
from apps.conversaciones.models import Conversacion
from apps.mensajes.models import Mensaje
import json
from django.utils import timezone


@method_decorator(csrf_exempt, name='dispatch')
class FlowWebhookView(View):
    """
    Vista para manejar webhooks de entrada a flujos
    URL: /webhook/{team_slug}/{flow_slug}/
    """
    
    def post(self, request, team_slug, flow_slug):
        try:
            # Obtener team y flow
            team = get_object_or_404(Team, slug=team_slug)
            flow = get_object_or_404(Flow, slug=flow_slug, team=team, is_active=True)
            
            # Parse del JSON
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
            # Extraer datos requeridos
            sender_id = data.get('sender_id')
            message = data.get('message', '')
            platform = data.get('platform', 'unknown')
            sender_name = data.get('sender_name', '')
            sender_phone = data.get('sender_phone', '')
            sender_email = data.get('sender_email', '')
            
            if not sender_id:
                return JsonResponse({'error': 'sender_id is required'}, status=400)
            
            # Obtener o crear Lead
            lead, lead_created = Lead.objects.get_or_create(
                plataforma=platform,
                plataforma_id=sender_id,
                defaults={
                    'nombre': sender_name,
                    'telefono': sender_phone,
                    'email': sender_email,
                    'fuente': 'mensaje_directo',
                    'asignado_a': team,
                }
            )
            
            # Si el lead existe, actualizar información si viene nueva
            if not lead_created:
                updated = False
                if sender_name and not lead.nombre:
                    lead.nombre = sender_name
                    updated = True
                if sender_phone and not lead.telefono:
                    lead.telefono = sender_phone
                    updated = True
                if sender_email and not lead.email:
                    lead.email = sender_email
                    updated = True
                if updated:
                    lead.save()
            
            # Obtener o crear sesión de conversación
            session, session_created = ConversationSession.objects.get_or_create(
                sender_id=sender_id,
                flow=flow,
                team=team,
                defaults={
                    'current_node': flow.start_node,
                    'lead': lead,
                    'platform': platform,
                    'platform_data': data.get('platform_data', {}),
                }
            )
            
            # Obtener o crear conversación
            if not session.conversacion:
                conversacion = Conversacion.create_for_flow(
                    lead=lead,
                    flow=flow,
                    platform=platform,
                    platform_thread_id=data.get('thread_id', ''),
                )
                session.conversacion = conversacion
                session.save()
            else:
                conversacion = session.conversacion
            
            
            # Después de obtener/crear session y conversacion
            if message:  # Solo si hay mensaje del usuario
                Mensaje.objects.create(
                    lead=lead,
                    conversacion=conversacion,
                    plataforma=platform,
                    tipo='mensaje_directo',
                    contenido=message,
                    es_respuesta=False,  # ← IMPORTANTE: es mensaje del usuario
                    respuesta_automatica=False,
                )

            # AHORA SÍ procesar el flujo
            response_data = self._process_flow_message(session, message, data)

            # Actualizar timestamps
            lead.ultima_interaccion = timezone.now()
            lead.save()
            conversacion.fecha_actualizacion = timezone.now()
            conversacion.save()
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def _process_flow_message(self, session, message, original_data):
        """Procesa un mensaje en el contexto del flujo"""
        current_node = session.current_node
        
        if not current_node:
            return {
                'error': 'No current node found',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
            }
        
        # --- Interceptar mensaje "menu principal" ---
        if message.strip().lower() == 'menu principal':
            try:
                menu_node = Node.objects.get(flow=session.flow, title__iexact='menu principal')
                session.current_node = menu_node
                session.save()
                
                response_message = self._prepare_response_message(menu_node, session)
                return {
                    'status': 'success',
                    'session_id': session.id,
                    'lead_id': session.lead.id,
                    'conversation_id': session.conversacion.id,
                    'current_node': {
                        'id': menu_node.id,
                        'title': menu_node.title,
                        'type': menu_node.type,
                    },
                    'collected_entity': None,
                    'next_node': {
                        'id': menu_node.id,
                        'title': menu_node.title,
                        'type': menu_node.type,
                        'collect_entity': menu_node.collect_entity.name if menu_node.collect_entity else None,
                        'collect_mode': menu_node.collect_entity_mode,
                    },
                    'response': response_message,
                    'flow_completed': False,
                    'context': session.context,
                }
            except Node.DoesNotExist:
                # Nodo 'menu principal' no existe en el flow
                pass
        # --- fin de interceptación ---

        
        # Si el nodo actual colecta una entidad, guardarla
        if current_node.collect_entity and message.strip():
            EntityValue.objects.update_or_create(
                entity=current_node.collect_entity,
                team=session.team,
                sender_id=session.sender_id,
                defaults={
                    'value': {
                        'raw': message,
                        'processed': message.strip(),
                        'node_id': current_node.id,
                        'timestamp': timezone.now().isoformat(),
                    }
                }
            )
            
            # Actualizar contexto de la sesión
            if 'collected_entities' not in session.context:
                session.context['collected_entities'] = {}
            session.context['collected_entities'][current_node.collect_entity.slug] = message.strip()
            session.save()
        
        # Determinar siguiente nodo
        next_node = session.get_next_node(message)
        
        # Actualizar sesión
        session.current_node = next_node
        session.updated_at = timezone.now()
        
        if not next_node:
            # Fin del flujo
            session.finish_session()
            session.save()
            
            return {
                'status': 'flow_completed',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
                'current_node': {
                    'id': current_node.id,
                    'title': current_node.title,
                    'type': current_node.type,
                },
                'collected_entity': current_node.collect_entity.name if current_node.collect_entity else None,
                'response': "Flujo completado. ¡Gracias por tu tiempo!",
                'next_node': None,
                'flow_completed': True,
            }
        else:
            session.save()
            
            # Preparar mensaje de respuesta con variables
            response_message = self._prepare_response_message(next_node, session)
            
            return {
                'status': 'success',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
                'current_node': {
                    'id': current_node.id,
                    'title': current_node.title,
                    'type': current_node.type,
                },
                'collected_entity': current_node.collect_entity.name if current_node.collect_entity else None,
                'next_node': {
                    'id': next_node.id,
                    'title': next_node.title,
                    'type': next_node.type,
                    'collect_entity': next_node.collect_entity.name if next_node.collect_entity else None,
                    'collect_mode': next_node.collect_entity_mode,
                },
                'response': response_message,
                'flow_completed': False,
                'context': session.context,
            }
    
    def _prepare_response_message(self, node, session):
        """Prepara el mensaje de respuesta reemplazando variables"""
        message = node.message_template or f"Nodo: {node.title}"
        
        # Reemplazar variables básicas
        variables = {
            'lead_name': session.lead.nombre or 'Usuario',
            'lead_phone': session.lead.telefono or '',
            'lead_email': session.lead.email or '',
        }
        
        # Agregar entidades colectadas desde EntityValue
        entity_values = EntityValue.objects.filter(
            team=session.team,
            sender_id=session.sender_id
        ).select_related('entity')
        
        for entity_value in entity_values:
            entity_slug = entity_value.entity.slug
            # Extraer el valor procesado o raw del JSON
            value_data = entity_value.value
            if isinstance(value_data, dict):
                value = value_data.get('processed') or value_data.get('raw', '')
            else:
                value = value_data
            variables[entity_slug] = value
        
        # También mantener el contexto de sesión como fallback
        if 'collected_entities' in session.context:
            for entity_slug, value in session.context['collected_entities'].items():
                if entity_slug not in variables:
                    variables[entity_slug] = value
        
        # Reemplazar variables en el mensaje
        # CORRECCIÓN: Buscar tanto {variable} como {{variable}}
        for var_name, var_value in variables.items():
            # Reemplazar formato simple {variable}
            message = message.replace(f'{{{var_name}}}', str(var_value))
            # Reemplazar formato doble {{variable}}
            message = message.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        return message

    def get(self, request, team_slug, flow_slug):
        """GET para obtener el flujo completo (con nodos y paths relevantes)"""
        team = get_object_or_404(Team, slug=team_slug)
        flow = get_object_or_404(Flow, slug=flow_slug, team=team)

        from .serializers import FlowDetailSerializer
        serializer = FlowDetailSerializer(flow, context={"request": request})

        return JsonResponse(serializer.data, safe=False)



class FlowProcessorView(APIView):
    """Vista existente mejorada para compatibilidad"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        flow_id = request.data.get("flow_id")
        sender_id = request.data.get("sender_id")
        message = request.data.get("message")

        try:
            flow = Flow.objects.get(id=flow_id)
        except Flow.DoesNotExist:
            return Response({"error": "Flujo no encontrado"}, status=404)

        # Obtener o crear sesión
        session, created = ConversationSession.objects.get_or_create(
            sender_id=sender_id,
            flow=flow,
            team=flow.team,
            defaults={"current_node": flow.start_node}
        )

        node = session.current_node

        if not node:
            return Response({"error": "No current node"}, status=400)

        # Si el nodo colecta entidad, guardarla
        if node.collect_entity:
            # Verificar que la entidad pertenece al mismo equipo
            entity = node.collect_entity
            if entity.team_id != flow.team_id:
                return Response({"error": "Entidad no pertenece al mismo equipo del flujo"}, status=400)

            # Guardar el valor solo si message no es None
            if message is not None:
                EntityValue.objects.update_or_create(
                    entity=entity,
                    team=flow.team,
                    sender_id=sender_id,
                    defaults={"value": {"raw": message}}
                )


        # Buscar siguiente nodo por paths
        next_node = session.get_next_node(message)

        # Actualizar sesión
        session.current_node = next_node
        session.save()

        response_message = None
        if next_node:
            response_message = next_node.message_template or f"Node: {next_node.title}"
        else:
            response_message = "Fin del flujo."

        return Response({
            "node": node.id,
            "collected_entity": node.collect_entity.name if node.collect_entity else None,
            "next_node": next_node.id if next_node else None,
            "response": response_message
        })


class FlowViewSet(viewsets.ModelViewSet):
    queryset = Flow.objects.all()
    serializer_class = FlowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Obtener equipos del usuario (Team, no TeamMember)
        user_teams = Team.objects.filter(members__user=user)

        # Filtrar flows solo de los equipos a los que pertenece
        return queryset.filter(team__in=user_teams)

    @action(detail=True, methods=['get'])
    def webhook_info(self, request, pk=None):
        """Endpoint para obtener información del webhook del flujo"""
        flow = self.get_object()
        return Response({
            'webhook_url': flow.webhook_url,
            'webhook_token': str(flow.webhook_token),
            'full_webhook_url': f"{request.build_absolute_uri('/')}{flow.webhook_url.lstrip('/')}",
            'is_active': flow.is_active,
        })


class NodeViewSet(viewsets.ModelViewSet):
    queryset = Node.objects.all()
    serializer_class = NodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        flow_id = self.request.query_params.get("flow")
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        return queryset

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data, partial=True)
        if not serializer.is_valid():
            print(serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def paths(self, request, pk=None):
        node = self.get_object()
        if request.method == "GET":
            paths = Path.objects.filter(node=node)
            serializer = PathSerializer(paths, many=True)
            return Response(serializer.data)

        # POST
        serializer = PathSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(node=node)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PathViewSet(viewsets.ModelViewSet):
    queryset = Path.objects.all()
    serializer_class = PathSerializer
    permission_classes = [IsAuthenticated]

class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrar por los equipos del usuario usando TeamMember
        if hasattr(self.request.user, 'teams'):
            # Obtener IDs de los equipos a los que pertenece el usuario
            user_team_ids = self.request.user.teams.values_list('team_id', flat=True)
            queryset = queryset.filter(team__id__in=user_team_ids)
        return queryset


    def _generate_suffix(self, length=4):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def _ensure_unique_slug(self, slug, team):
        base_slug = slug
        while Entity.objects.filter(slug=slug, team=team).exists():
            suffix = self._generate_suffix()
            slug = f"{base_slug}_{suffix}"
        return slug

    def perform_create(self, serializer):
        # Tomar el slug enviado por el frontend y añadir sufijo
        team = serializer.validated_data['team']
        slug = serializer.validated_data.get('slug', '')
        slug = self._ensure_unique_slug(slug, team)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        # También se puede actualizar el slug si cambió el nombre
        team = serializer.instance.team
        slug = serializer.validated_data.get('slug', serializer.instance.slug)
        slug = self._ensure_unique_slug(slug, team)
        serializer.save(slug=slug)