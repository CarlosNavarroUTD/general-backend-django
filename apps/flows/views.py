from rest_framework import viewsets
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
from apps.conversaciones.models import Conversacion, Message, MessageDirection
import json
from django.utils import timezone
import unicodedata

def normalize(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower().strip()


@method_decorator(csrf_exempt, name='dispatch')
class FlowWebhookView(View):
    """
    Vista para manejar webhooks de entrada a flujos
    URL: /webhook/{team_slug}/{flow_slug}/
    """
    
    def post(self, request, team_slug, flow_slug):
        try:
            from .models import Flow, ConversationSession, EntityValue
            
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
                from apps.conversaciones.utils import get_or_create_conversation
                conversacion, _ = get_or_create_conversation(
                    sender_id=sender_id,
                    team=team,
                    platform=platform,
                    lead=lead
                )
                session.conversacion = conversacion
                session.save()
            else:
                conversacion = session.conversacion
            
            
            # Después de obtener/crear session y conversacion
            if message:  # Solo si hay mensaje del usuario
                from apps.conversaciones.models import MessageDirection, MessageType
                
                Message.objects.create(
                    conversacion=conversacion,
                    direction=MessageDirection.INBOUND,  # Mensaje entrante
                    type=MessageType.TEXT,
                    content=message,
                    sender_name=sender_name,
                    metadata={
                        'platform': platform,
                        'is_automated': False,
                        'source': 'webhook',
                    },
                    external_id=data.get('message_id'),  # Si viene un ID externo
                )
                
                # Actualizar timestamp de la conversación
                conversacion.last_message_at = timezone.now()
                conversacion.save(update_fields=['last_message_at'])

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
    
    def _match_multiple_choice_option(self, message, entity):
        """
        Intenta hacer match del mensaje del usuario con una opción de multiple choice
        Formato esperado: [{ 'key': str, 'label': str, 'keywords': [str] }]
        Retorna: (matched_option_dict, option_index) o (None, None) si no hay match
        """
        if not entity.options:
            return None, None
        
        message_lower = message.strip().lower()
        
        # 1. Intentar match por número (1, 2, 3, etc.)
        if message_lower.isdigit():
            index = int(message_lower) - 1  # Convertir a índice base-0
            if 0 <= index < len(entity.options):
                return entity.options[index], index
        
        # 2. Intentar match usando las opciones
        for idx, option in enumerate(entity.options):
            # Obtener label y keywords
            label = option.get('label', '').lower()
            key = option.get('key', '').lower()
            keywords = option.get('keywords', [])
            
            # Match exacto con label
            if message_lower == label:
                return option, idx
            
            # Match exacto con key
            if message_lower == key:
                return option, idx
            
            # Match si el mensaje contiene el label completo
            if label and label in message_lower:
                return option, idx
            
            # Match si el label contiene el mensaje (para respuestas cortas)
            if label and message_lower in label and len(message_lower) >= 3:
                return option, idx
            
            # Match por keywords
            if keywords:
                for keyword in keywords:
                    keyword_lower = str(keyword).lower()
                    if keyword_lower == message_lower:
                        return option, idx
                    if keyword_lower in message_lower or message_lower in keyword_lower:
                        return option, idx
            
            # Match por palabras individuales en label (mínimo 3 caracteres)
            if label:
                label_words = set(word for word in label.split() if len(word) >= 3)
                message_words = set(word for word in message_lower.split() if len(word) >= 3)
                
                # Si hay coincidencia de palabras significativas
                if label_words and message_words:
                    common_words = label_words & message_words
                    if common_words:
                        return option, idx
        
        return None, None
    
    def _process_flow_message(self, session, message, original_data):
        """Procesa un mensaje en el contexto del flujo"""
        from .models import Node, EntityValue
        
        current_node = session.current_node
        
        # Si no hay nodo actual, reiniciar automáticamente
        if not current_node:
            # Reiniciar sesión automáticamente
            EntityValue.objects.filter(
                team=session.team,
                sender_id=session.sender_id
            ).delete()
            
            session.context = {'collected_entities': {}}
            session.current_node = session.flow.start_node
            session.save()
            
            # Avanzar al siguiente nodo
            next_node = session.get_next_node("")
            if next_node:
                session.current_node = next_node
                session.save()
                response_message = self._prepare_response_message(next_node, session)
                
                return {
                    'status': 'auto_restarted',
                    'session_id': session.id,
                    'lead_id': session.lead.id,
                    'conversation_id': session.conversacion.id,
                    'current_node': {
                        'id': next_node.id,
                        'title': next_node.title,
                        'type': next_node.type,
                    },
                    'response': response_message,
                    'message': 'Conversación reiniciada automáticamente',
                }
            else:
                return {
                    'error': 'No se pudo reiniciar el flujo',
                    'session_id': session.id,
                    'lead_id': session.lead.id,
                    'conversation_id': session.conversacion.id,
                }
        
        # --- Interceptar mensaje que coincida exactamente con título de nodo ---
        try:
            matching_node = Node.objects.get(flow=session.flow, title=message.strip())
            session.current_node = matching_node
            session.save()
            
            response_message = self._prepare_response_message(matching_node, session)
            return {
                'status': 'success',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
                'current_node': {
                    'id': matching_node.id,
                    'title': matching_node.title,
                    'type': matching_node.type,
                },
                'collected_entity': None,
                'next_node': {
                    'id': matching_node.id,
                    'title': matching_node.title,
                    'type': matching_node.type,
                    'collect_entity': matching_node.collect_entity.name if matching_node.collect_entity else None,
                    'collect_mode': matching_node.collect_entity_mode,
                },
                'response': response_message,
                'flow_completed': False,
                'context': session.context,
            }
        except Node.DoesNotExist:
            pass
            
        # --- Interceptar mensaje "menu principal" ---
        if normalize(message) == 'menu principal':
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
                pass

        # --- Interceptar mensaje "reiniciar historial" ---
        if message.strip().lower() == 'reiniciar historial':
            from .models import EntityValue
            
            # Borrar todas las entidades colectadas de este sender
            EntityValue.objects.filter(
                team=session.team,
                sender_id=session.sender_id
            ).delete()
            
            # Limpiar contexto
            session.context = {
                'collected_entities': {},
                'reset_at': timezone.now().isoformat()
            }
            
            # Reiniciar al nodo de inicio
            start_node = session.flow.start_node
            session.current_node = start_node
            session.is_finished = False
            session.save()
            
            # Agregar mensaje de reinicio a la conversación
            from apps.conversaciones.utils import add_message_to_conversation
            add_message_to_conversation(
                conversacion=session.conversacion,
                content="🔄 Historial reiniciado. Comenzando nueva conversación...",
                direction='OUTBOUND',
                message_type='TEXT'
            )
            
            # Avanzar al siguiente nodo después del START
            next_node_after_start = session.get_next_node("")
            
            if next_node_after_start:
                session.current_node = next_node_after_start
                session.save()
                response_message = self._prepare_response_message(next_node_after_start, session)
                current_node_info = {
                    'id': next_node_after_start.id,
                    'title': next_node_after_start.title,
                    'type': next_node_after_start.type,
                }
            else:
                response_message = self._prepare_response_message(start_node, session)
                current_node_info = {
                    'id': start_node.id,
                    'title': start_node.title,
                    'type': start_node.type,
                }
            
            return {
                'status': 'history_reset',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
                'current_node': current_node_info,
                'response': response_message,
                'message': 'Historial reiniciado exitosamente. Comenzando desde el inicio.'
            }

        
        # Si el nodo actual colecta una entidad, procesarla
        collected_value = None
        validation_error = None
        
        if current_node.collect_entity and message.strip():
            entity = current_node.collect_entity
            message_stripped = message.strip()
            
            # Validar si es multiple choice
            if entity.type == 'MULTIPLE_CHOICE' and entity.options:
                matched_option, option_index = self._match_multiple_choice_option(message_stripped, entity)
                
                if matched_option:
                    # Guardar el label si existe, sino el key
                    label = matched_option.get('label', '').strip()
                    if not label:
                        label = matched_option.get('key', '')
                    collected_value = label
                else:
                    # Opción inválida, preparar mensaje de error
                    validation_error = f"⚠️ Opción no válida. Por favor selecciona una de las opciones disponibles:\n\n"
                    for idx, option in enumerate(entity.options, 1):
                        label = option.get('label', '').strip()
                        if not label:
                            label = option.get('key', f'Opción {idx}')
                        validation_error += f"{idx}. {label}\n"
                    
                    return {
                        'status': 'validation_error',
                        'session_id': session.id,
                        'lead_id': session.lead.id,
                        'conversation_id': session.conversacion.id,
                        'current_node': {
                            'id': current_node.id,
                            'title': current_node.title,
                            'type': current_node.type,
                        },
                        'error': validation_error,
                        'response': validation_error,
                        'flow_completed': False,
                        'context': session.context,
                    }
            else:
                # Para otros tipos de entidades, guardar tal cual
                collected_value = message_stripped
            
            # Guardar el valor validado
            if collected_value:
                EntityValue.objects.update_or_create(
                    entity=entity,
                    team=session.team,
                    sender_id=session.sender_id,
                    defaults={
                        'value': {
                            'raw': message,
                            'processed': collected_value,
                            'node_id': current_node.id,
                            'timestamp': timezone.now().isoformat(),
                            'entity_type': entity.type,
                        }
                    }
                )
                
                # Actualizar contexto de la sesión
                if 'collected_entities' not in session.context:
                    session.context['collected_entities'] = {}
                session.context['collected_entities'][entity.slug] = collected_value
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
                'response': "Si necesitas más ayuda, puedes escribir 'menú principal' para volver al inicio.",
                'next_node': None,
                'flow_completed': True,
            }
        else:
            session.save()
            
            # Preparar mensaje de respuesta con variables y opciones de multiple choice
            response_message = self._prepare_response_message(next_node, session)
            
            # Preparar información adicional sobre la entidad a colectar
            entity_info = None
            if next_node.collect_entity:
                entity_info = {
                    'name': next_node.collect_entity.name,
                    'slug': next_node.collect_entity.slug,
                    'type': next_node.collect_entity.type,
                    'options': next_node.collect_entity.options if next_node.collect_entity.type == 'MULTIPLE_CHOICE' else None,
                }

            # --- Agregar paths del nodo actual ---
            from .models import Path  # asegúrate de tenerlo definido
            paths = current_node.outgoing_paths.select_related('target').all() if hasattr(current_node, 'outgoing_paths') else []
            paths_data = [
                {
                    'id': p.id,
                    'conditions': p.conditions,
                    'target_node': {
                        'id': p.target.id,
                        'message': getattr(p.target, 'message', None)
                    }
                }
                for p in paths
            ]

            # --- Respuesta final ---
            return {
                'status': 'success',
                'session_id': session.id,
                'lead_id': session.lead.id,
                'conversation_id': session.conversacion.id,
                'current_node': {
                    'id': current_node.id,
                    'title': current_node.title,
                    'type': current_node.type,
                    'paths': paths_data,  # 👈 agregado aquí
                },
                'collected_entity': current_node.collect_entity.name if current_node.collect_entity else None,
                'collected_value': collected_value,
                'next_node': {
                    'id': next_node.id,
                    'title': next_node.title,
                    'type': next_node.type,
                    'collect_entity': next_node.collect_entity.name if next_node.collect_entity else None,
                    'collect_mode': next_node.collect_entity_mode,
                    'entity_info': entity_info,
                },
                'response': response_message,
                'flow_completed': False,
                'context': session.context,
            }

    
    def _prepare_response_message(self, node, session):
        """Prepara el mensaje de respuesta reemplazando variables y añadiendo opciones de multiple choice"""
        from .models import EntityValue
        
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
        for var_name, var_value in variables.items():
            message = message.replace(f'{{{var_name}}}', str(var_value))
            message = message.replace(f'{{{{{var_name}}}}}', str(var_value))
        
        # Si este nodo colecta una entidad de tipo multiple_choice, agregar las opciones
        if node.collect_entity:
            entity = node.collect_entity
            
            # Verificar que sea MULTIPLE_CHOICE (mayúsculas como en EntityType.choices)
            if entity.type == 'MULTIPLE_CHOICE' and entity.options:
                # Verificar que options sea una lista con elementos
                if isinstance(entity.options, list) and len(entity.options) > 0:
                    message += "\n\n"
                    for idx, option in enumerate(entity.options, 1):
                        # Obtener el label de la opción, usar key si label está vacío
                        if isinstance(option, dict):
                            label = option.get('label', '').strip()
                            if not label:  # Si label está vacío, usar key
                                label = option.get('key', f'Opción {idx}')
                        else:
                            label = str(option)
                        message += f"{idx}. {label}"
        
        return message

    def get(self, request, team_slug, flow_slug):
        """GET para obtener el flujo completo (con nodos y paths relevantes)"""
        from .models import Flow
        from .serializers import FlowDetailSerializer
        
        team = get_object_or_404(Team, slug=team_slug)
        flow = get_object_or_404(Flow, slug=flow_slug, team=team)

        serializer = FlowDetailSerializer(flow, context={"request": request})

        return JsonResponse(serializer.data, safe=False)


class FlowProcessorView(APIView):
    """Vista existente mejorada para compatibilidad"""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        from .models import Flow, ConversationSession, EntityValue
        
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
            entity = node.collect_entity
            if entity.team_id != flow.team_id:
                return Response({"error": "Entidad no pertenece al mismo equipo del flujo"}, status=400)

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import Flow
        
        user = self.request.user
        user_teams = Team.objects.filter(members__user=user)
        return Flow.objects.filter(team__in=user_teams)
    
    def get_serializer_class(self):
        from .serializers import FlowSerializer
        return FlowSerializer

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import Node
        
        queryset = Node.objects.all()
        flow_id = self.request.query_params.get("flow")
        if flow_id:
            queryset = queryset.filter(flow_id=flow_id)
        return queryset
    
    def get_serializer_class(self):
        from .serializers import NodeSerializer
        return NodeSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(instance=self.get_object(), data=request.data, partial=True)
        if not serializer.is_valid():
            print(serializer.errors)
            return Response(serializer.errors, status=400)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def paths(self, request, pk=None):
        from .models import Path
        from .serializers import PathSerializer
        
        node = self.get_object()
        if request.method == "GET":
            paths = Path.objects.filter(node=node)
            serializer = PathSerializer(paths, many=True)
            return Response(serializer.data)

        serializer = PathSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(node=node)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PathViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        from .models import Path
        return Path.objects.all()
    
    def get_serializer_class(self):
        from .serializers import PathSerializer
        return PathSerializer

class EntityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from .models import Entity
        
        queryset = Entity.objects.all()
        if hasattr(self.request.user, 'teams'):
            user_team_ids = self.request.user.teams.values_list('team_id', flat=True)
            queryset = queryset.filter(team__id__in=user_team_ids)
        return queryset
    
    def get_serializer_class(self):
        from .serializers import EntitySerializer
        return EntitySerializer

    def _generate_suffix(self, length=4):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def perform_create(self, serializer):
        from .models import Entity
        
        team = serializer.validated_data['team']
        slug = serializer.validated_data.get('slug', '')
        slug = self._ensure_unique_slug(slug, team, Entity)
        serializer.save(slug=slug)

    def perform_update(self, serializer):
        from .models import Entity
        
        team = serializer.instance.team
        slug = serializer.validated_data.get('slug', serializer.instance.slug)
        slug = self._ensure_unique_slug(slug, team, Entity)
        serializer.save(slug=slug)
    
    def _ensure_unique_slug(self, slug, team, Entity):
        base_slug = slug
        while Entity.objects.filter(slug=slug, team=team).exists():
            suffix = self._generate_suffix()
            slug = f"{base_slug}_{suffix}"
        return slug