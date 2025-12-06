from django.db import models
from django.contrib.auth import get_user_model
from apps.teams.models import Team
from django.utils.text import slugify
import uuid

def gen_slug():
    return str(uuid.uuid4())

User = get_user_model()

# --- Enumeraciones ---
class EntityType(models.TextChoices):
    TEXT = "TEXT", "Texto"
    NUMBER = "NUMBER", "Número"
    DATE = "DATE", "Fecha"
    BOOLEAN = "BOOLEAN", "Booleano"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE", "Opción múltiple"
    EMAIL = "EMAIL", "Email"
    PHONE = "PHONE", "Teléfono"

class NodeType(models.TextChoices):
    START = "START", "Inicio"
    END = "END", "Fin"
    QUESTION = "QUESTION", "Pregunta"
    ACTION = "ACTION", "Acción"
    WEBHOOK = "WEBHOOK", "Webhook"
    DELAY = "DELAY", "Delay"
    SCRIPT = "SCRIPT", "Script"

class CollectMode(models.TextChoices):
    REQUIRED = "REQUIRED", "Requerido"
    OPTIONAL = "OPTIONAL", "Opcional"
    NONE = "NONE", "Ninguno"

class FlowStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    FINISHED = "FINISHED", "Finalizado"

# --- Models ---
class Entity(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    type = models.CharField(max_length=20, choices=EntityType.choices)
    required_format = models.CharField(max_length=50, blank=True, null=True)
    options = models.JSONField(
        blank=True, null=True,
        help_text="Solo para multiple choice: [{ 'key': str, 'label': str, 'keywords': [str] }]"
    )
    auto_extract = models.BooleanField(default=False)
    fuzzy_aliases = models.JSONField(blank=True, null=True, help_text="Lista de sinónimos o alias")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='entities')

    class Meta:
        unique_together = ('slug', 'team')

    def __str__(self):
        return f"{self.name} ({self.type})"

class EntityValue(models.Model):
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="values")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="entity_values")
    sender_id = models.CharField(max_length=150, help_text="ID único del remitente (usuario/lead)")
    value = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entity', 'team', 'sender_id')

    def __str__(self):
        return f"{self.sender_id} - {self.entity.name}: {self.value}"

class Flow(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    webhook_token = models.UUIDField(default=uuid.uuid4, help_text="Token único para seguridad del webhook", blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(default=1)
    metadata = models.JSONField(blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='flows')

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Flow.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def webhook_url(self):
        """Genera la URL del webhook para este flujo"""
        return f"/webhook/{self.team.slug}/{self.slug}/"

    @property
    def start_node(self):
        """Obtiene el nodo de inicio del flujo"""
        return self.nodes.filter(type=NodeType.START).first()

    def __str__(self):
        return self.name

class Node(models.Model):
    flow = models.ForeignKey(Flow, related_name="nodes", on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=NodeType.choices)
    title = models.CharField(max_length=150)
    message_template = models.TextField(blank=True, help_text="Texto con variables {{entity}}")
    collect_entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)
    collect_entity_mode = models.CharField(max_length=20, choices=CollectMode.choices, default=CollectMode.NONE)
    position = models.JSONField(default=dict, help_text="Coordenadas {x, y}")
    ui_settings = models.JSONField(blank=True, null=True)
    default_path = models.ForeignKey("Path", null=True, blank=True, on_delete=models.SET_NULL, related_name="+") 

    def __str__(self):
        return f"{self.title} ({self.type})"

class ConversationSession(models.Model):
    """Sesión de conversación mejorada con referencia a Lead y Conversación"""
    sender_id = models.CharField(max_length=150)
    flow = models.ForeignKey(Flow, on_delete=models.CASCADE)
    current_node = models.ForeignKey(Node, on_delete=models.SET_NULL, null=True, blank=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="sessions")
    
    # Nueva conexión con Lead y Conversación
    lead = models.ForeignKey('leads.Lead', on_delete=models.CASCADE, null=True, blank=True, related_name="flow_sessions")
    conversacion = models.ForeignKey('conversaciones.Conversacion', on_delete=models.CASCADE, null=True, blank=True, related_name="flow_sessions")
    
    # Estado de la sesión
    status = models.CharField(max_length=20, choices=FlowStatus.choices, default=FlowStatus.ACTIVE)
    
    # Metadatos de la sesión
    context = models.JSONField(default=dict, help_text="Contexto y variables de la sesión")
    platform = models.CharField(max_length=50, blank=True, help_text="Plataforma de origen (whatsapp, telegram, etc)")
    platform_data = models.JSONField(blank=True, null=True, help_text="Datos específicos de la plataforma")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('sender_id', 'flow', 'team')

    def __str__(self):
        return f"{self.sender_id} in {self.flow.name} at {self.current_node}"

    def finish_session(self):
        """Finaliza la sesión del flujo"""
        from django.utils import timezone
        self.status = FlowStatus.FINISHED
        self.finished_at = timezone.now()
        self.save()

    def get_next_node(self, user_message=None):
        """
        Determina el siguiente nodo basado en los paths y condiciones.
        
        Prioridad:
        1. Paths con condición cumplida (independiente de 'enabled')
        2. Paths habilitados sin condición
        3. Default path habilitado
        4. Permanecer en el nodo actual si es de tipo QUESTION y no hay paths válidos
        5. END node si no hay alternativas
        """

        if not self.current_node:
            print("No hay nodo actual.")
            return None

        paths = self.current_node.paths.all().order_by("order")
        print(f"Evaluando {len(paths)} paths para el nodo {self.current_node.id}")

        # Debug: Mostrar entidades recolectadas
        collected_entities = self.get_collected_entities_debug()
        print(f"Entidades recolectadas: {collected_entities}")

        # --- 1. Paths condicionales ---
        conditional_paths = [p for p in paths if p.condition and p.enabled]
        print(f"Paths condicionales encontrados: {len(conditional_paths)}")
        
        for path in conditional_paths:
            try:
                result = self.evaluate_condition(path.condition, message_text=user_message)  # ✅ Pasa el mensaje
                print(f"Path condicional {path.id} ('{path.label}') -> {getattr(path.target_node, 'id', None)}: {result}")
                if result and path.target_node:
                    print(f"✅ Siguiendo path condicional {path.id} -> {path.target_node.id}")
                    return path.target_node
            except Exception as e:
                print(f"❌ Error evaluando path condicional {path.id}: {e}")
                continue

        # --- 2. Paths habilitados sin condición ---
        unconditional_paths = [p for p in paths if not p.condition and p.enabled]
        print(f"Paths sin condición encontrados: {len(unconditional_paths)}")
        
        for path in unconditional_paths:
            if path.target_node:
                print(f"✅ Siguiendo path sin condición {path.id} -> {path.target_node.id}")
                return path.target_node

        # --- 3. Default path ---
        default_path = getattr(self.current_node, "default_path", None)
        if default_path and getattr(default_path, "enabled", True) and default_path.target_node:
            print(f"✅ Siguiendo default path {default_path.id} -> {default_path.target_node.id}")
            return default_path.target_node

        # --- 4. Si es nodo QUESTION sin paths válidos, permanecer ---
        if self.current_node.type == "QUESTION":
            print(f"⚠️  Nodo QUESTION {self.current_node.id} sin paths válidos - permaneciendo en el nodo")
            return self.current_node

        # --- 5. Nodo END ---
        if self.current_node.type == "END":
            print(f"🏁 Se llegó al nodo END {self.current_node.id}")
            return None

        # --- Si no hay paths válidos ---
        print(f"❌ No se encontró path válido desde el nodo {self.current_node.id}")
        return None

    def evaluate_condition(self, condition, message_text=None):
        """
        Evalúa un objeto de condición tipo JSON.
        Soporta múltiples tipos de condiciones tanto basadas en entidades como en respuestas directas.
        """
        print(f"🔍 Evaluando condición: {condition}")
        
        if not isinstance(condition, dict):
            print(f"❌ Condición no es un diccionario válido")
            return False
            
        if condition.get("type") != "conditions":
            print(f"❌ Tipo de condición no soportado: {condition.get('type')}")
            return False
            
        conditions_list = condition.get("conditions", [])
        if not conditions_list:
            print(f"❌ No hay condiciones en la lista")
            return False
            
        # Obtener la lógica de evaluación (AND/OR)
        logic = condition.get("logic", "single")
        print(f"📋 Lógica de evaluación: {logic}")
        
        results = []
        
        for i, c in enumerate(conditions_list):
            print(f"📝 Evaluando condición {i+1}/{len(conditions_list)}: {c}")
            
            condition_type = c.get("type")
            result = self._evaluate_single_condition(c, message_text=message_text)
            results.append(result)
            
            print(f"{'✅' if result else '❌'} Resultado de condición {i+1}: {result}")
            
            # Si la lógica es AND y encontramos un false, retornamos false inmediatamente
            if logic == "single" and not result:
                print(f"❌ Lógica AND: condición falló, retornando False")
                return False
                
        # Evaluar resultado final basado en la lógica
        if logic == "single":  # AND logic
            final_result = all(results)
        else:  # OR logic (si se implementa en el futuro)
            final_result = any(results)
            
        print(f"{'✅' if final_result else '❌'} Resultado final de todas las condiciones: {final_result}")
        return final_result

    def _evaluate_single_condition(self, c, message_text=None):  # ✅ Agregar parámetro
        """
        Evalúa una condición individual.
        Retorna True si la condición se cumple, False en caso contrario.
        """
        condition_type = c.get("type")
        
        # ========== CONDICIONES BASADAS EN ENTIDADES ==========
        if condition_type in ["entity_exists", "entity_equals", "entity_contains", 
                            "entity_greater", "entity_less", "entity_is_any_of"]:
            return self._evaluate_entity_condition(c)
        
        # ========== CONDICIONES BASADAS EN RESPUESTA DIRECTA ==========
        elif condition_type in ["message_equals", "message_contains", "message_starts_with",
                            "message_ends_with", "message_is_any_of", "message_matches_regex"]:
            return self._evaluate_message_condition(c, message_text=message_text)  # ✅ Pasar message_text
        
        else:
            print(f"❌ Tipo de condición no soportado: {condition_type}")
            return False

    def _evaluate_entity_condition(self, c):
        """
        Evalúa condiciones basadas en entidades recolectadas.
        """
        condition_type = c.get("type")
        entity_id = c.get("entity_id")
        
        if not entity_id:
            print(f"❌ Condición de entidad sin entity_id")
            return False
        
        # ENTITY_EXISTS: Verifica si la entidad fue recolectada
        if condition_type == "entity_exists":
            collected_ids = self.get_collected_entity_ids()
            print(f"🔎 Buscando entity_id {entity_id} en collected_ids: {collected_ids}")
            exists = entity_id in collected_ids
            print(f"{'✅' if exists else '❌'} Entity {entity_id} {'encontrada' if exists else 'NO encontrada'}")
            return exists
        
        # Para el resto de condiciones, necesitamos el valor de la entidad
        entity_value = self.get_entity_value(entity_id)
        
        if entity_value is None:
            print(f"❌ Entity {entity_id} no tiene valor")
            return False
        
        # Normalizar el valor de la entidad
        entity_value_str = str(entity_value).strip()
        
        # ENTITY_EQUALS: Verifica si la entidad es igual a un valor específico
        if condition_type == "entity_equals":
            expected_value = c.get("value")
            if expected_value is None:
                print(f"❌ Condición entity_equals sin valor esperado")
                return False
            
            entity_value_clean = entity_value_str.lower()
            expected_value_clean = str(expected_value).strip().lower()
            
            match = entity_value_clean == expected_value_clean
            print(f"{'✅' if match else '❌'} Entity {entity_id}: '{entity_value_clean}' {'==' if match else '!='} '{expected_value_clean}'")
            return match
        
        # ENTITY_CONTAINS: Verifica si la entidad contiene un texto
        if condition_type == "entity_contains":
            search_value = c.get("value")
            if search_value is None:
                print(f"❌ Condición entity_contains sin valor de búsqueda")
                return False
            
            entity_value_clean = entity_value_str.lower()
            search_value_clean = str(search_value).strip().lower()
            
            contains = search_value_clean in entity_value_clean
            print(f"{'✅' if contains else '❌'} Entity {entity_id}: '{entity_value_clean}' {'contiene' if contains else 'no contiene'} '{search_value_clean}'")
            return contains
        
        # ENTITY_GREATER: Verifica si la entidad es mayor que un valor
        if condition_type == "entity_greater":
            try:
                expected_value = c.get("value")
                if expected_value is None:
                    print(f"❌ Condición entity_greater sin valor esperado")
                    return False
                
                # Intentar convertir a número
                entity_num = float(entity_value_str)
                expected_num = float(expected_value)
                
                is_greater = entity_num > expected_num
                print(f"{'✅' if is_greater else '❌'} Entity {entity_id}: {entity_num} {'>' if is_greater else '<='} {expected_num}")
                return is_greater
            except (ValueError, TypeError) as e:
                print(f"❌ Error convirtiendo a número para entity_greater: {e}")
                return False
        
        # ENTITY_LESS: Verifica si la entidad es menor que un valor
        if condition_type == "entity_less":
            try:
                expected_value = c.get("value")
                if expected_value is None:
                    print(f"❌ Condición entity_less sin valor esperado")
                    return False
                
                # Intentar convertir a número
                entity_num = float(entity_value_str)
                expected_num = float(expected_value)
                
                is_less = entity_num < expected_num
                print(f"{'✅' if is_less else '❌'} Entity {entity_id}: {entity_num} {'<' if is_less else '>='} {expected_num}")
                return is_less
            except (ValueError, TypeError) as e:
                print(f"❌ Error convirtiendo a número para entity_less: {e}")
                return False
        
        # ENTITY_IS_ANY_OF: Verifica si la entidad es alguno de los valores en una lista
        if condition_type == "entity_is_any_of":
            values_list = c.get("values", [])
            if not values_list:
                print(f"❌ Condición entity_is_any_of sin lista de valores")
                return False
            
            entity_value_clean = entity_value_str.lower()
            # Normalizar todos los valores de la lista
            normalized_values = [str(v).strip().lower() for v in values_list]
            
            is_any_of = entity_value_clean in normalized_values
            print(f"{'✅' if is_any_of else '❌'} Entity {entity_id}: '{entity_value_clean}' {'está en' if is_any_of else 'no está en'} {normalized_values}")
            return is_any_of
        
        return False

    def _evaluate_message_condition(self, c, message_text=None):
        """
        Evalúa condiciones basadas en el mensaje recibido del usuario.
        - Usa message_text si se pasa directamente.
        - Si no se pasa, cae al último mensaje en DB como fallback.
        """
        condition_type = c.get("type")

        if message_text is None:
            # fallback: DB
            last_message = self._get_last_user_message()
            if not last_message:
                print(f"❌ No hay mensaje del usuario para evaluar")
                return False
            message_clean = str(last_message).strip()
        else:
            message_clean = str(message_text).strip()

        message_lower = message_clean.lower()
        print(f"📨 Evaluando mensaje: '{message_clean}'")
        
        # MESSAGE_EQUALS: El mensaje es exactamente igual a un valor
        if condition_type == "message_equals":
            expected_value = c.get("value")
            if expected_value is None:
                print(f"❌ Condición message_equals sin valor esperado")
                return False
            
            expected_clean = str(expected_value).strip().lower()
            match = message_lower == expected_clean
            print(f"{'✅' if match else '❌'} Mensaje: '{message_lower}' {'==' if match else '!='} '{expected_clean}'")
            return match
        
        # MESSAGE_CONTAINS: El mensaje contiene un texto específico
        if condition_type == "message_contains":
            search_value = c.get("value")
            if search_value is None:
                print(f"❌ Condición message_contains sin valor de búsqueda")
                return False
            
            search_clean = str(search_value).strip().lower()
            contains = search_clean in message_lower
            print(f"{'✅' if contains else '❌'} Mensaje {'contiene' if contains else 'no contiene'} '{search_clean}'")
            return contains
        
        # MESSAGE_STARTS_WITH: El mensaje comienza con un texto específico
        if condition_type == "message_starts_with":
            prefix = c.get("value")
            if prefix is None:
                print(f"❌ Condición message_starts_with sin valor esperado")
                return False
            
            prefix_clean = str(prefix).strip().lower()
            starts = message_lower.startswith(prefix_clean)
            print(f"{'✅' if starts else '❌'} Mensaje {'comienza con' if starts else 'no comienza con'} '{prefix_clean}'")
            return starts
        
        # MESSAGE_ENDS_WITH: El mensaje termina con un texto específico
        if condition_type == "message_ends_with":
            suffix = c.get("value")
            if suffix is None:
                print(f"❌ Condición message_ends_with sin valor esperado")
                return False
            
            suffix_clean = str(suffix).strip().lower()
            ends = message_lower.endswith(suffix_clean)
            print(f"{'✅' if ends else '❌'} Mensaje {'termina con' if ends else 'no termina con'} '{suffix_clean}'")
            return ends
        
        # MESSAGE_IS_ANY_OF: El mensaje es alguno de los valores en una lista
        if condition_type == "message_is_any_of":
            values_list = c.get("values", [])
            if not values_list:
                print(f"❌ Condición message_is_any_of sin lista de valores")
                return False
            
            # Normalizar todos los valores de la lista
            normalized_values = [str(v).strip().lower() for v in values_list]
            
            is_any_of = message_lower in normalized_values
            print(f"{'✅' if is_any_of else '❌'} Mensaje: '{message_lower}' {'está en' if is_any_of else 'no está en'} {normalized_values}")
            return is_any_of
        
        # MESSAGE_MATCHES_REGEX: El mensaje coincide con una expresión regular
        if condition_type == "message_matches_regex":
            import re
            pattern = c.get("value")
            if pattern is None:
                print(f"❌ Condición message_matches_regex sin patrón")
                return False
            
            try:
                regex = re.compile(str(pattern), re.IGNORECASE)
                matches = bool(regex.search(message_clean))
                print(f"{'✅' if matches else '❌'} Mensaje {'coincide con' if matches else 'no coincide con'} regex '{pattern}'")
                return matches
            except re.error as e:
                print(f"❌ Error en expresión regular '{pattern}': {e}")
                return False
        
        return False

    def _get_last_user_message(self):
        """
        Obtiene el último mensaje del usuario (entrante/inbound)
        usando el modelo Message de conversaciones
        """
        if self.conversacion:
            # Buscar en los mensajes de la conversación actual
            last_message = (
                self.conversacion.messages
                .filter(direction='INBOUND')  # Solo mensajes entrantes
                .order_by('-created_at')
                .first()
            )
        else:
            # Fallback: buscar en todas las conversaciones del lead
            from apps.conversaciones.models import Message, MessageDirection
            
            if self.lead:
                last_message = (
                    Message.objects
                    .filter(
                        conversacion__lead=self.lead,
                        direction=MessageDirection.INBOUND
                    )
                    .order_by('-created_at')
                    .first()
                )
            else:
                last_message = None

        if last_message:
            print(f"📨 Último mensaje del usuario encontrado: '{last_message.content[:50]}...'")
            return last_message.content
        
        print("❌ No se encontró ningún mensaje del usuario")
        return None
                    
    def get_collected_entity_ids(self):
        """
        Retorna la lista de IDs de entidades recolectadas en esta sesión.
        """
        try:
            # Obtener los EntityValues para este sender_id y team
            entity_values = EntityValue.objects.filter(
                sender_id=self.sender_id,
                team=self.team
            ).values_list('entity_id', flat=True)
            
            collected_ids = list(entity_values)
            print(f"📊 Entidades recolectadas para sender_id {self.sender_id}: {collected_ids}")
            return collected_ids
        except Exception as e:
            print(f"❌ Error obteniendo entidades recolectadas: {e}")
            return []
    
    def get_entity_value(self, entity_id):
        """
        Obtiene el valor de una entidad específica para esta sesión.
        """
        try:
            entity_value = EntityValue.objects.get(
                entity_id=entity_id,
                sender_id=self.sender_id,
                team=self.team
            )
            raw_value = entity_value.value
            print(f"🔍 Valor raw encontrado para entity {entity_id}: '{raw_value}'")
            
            # Si el valor es un diccionario con estructura {'raw': 'valor', 'processed': 'valor'...}
            if isinstance(raw_value, dict):
                if 'processed' in raw_value:
                    processed_value = raw_value['processed']
                    print(f"✅ Extrayendo valor 'processed' para entity {entity_id}: '{processed_value}'")
                    return processed_value
                elif 'raw' in raw_value:
                    raw_text = raw_value['raw']
                    print(f"✅ Extrayendo valor 'raw' para entity {entity_id}: '{raw_text}'")
                    return raw_text
                else:
                    print(f"⚠️  Diccionario sin 'processed' ni 'raw', usando el diccionario completo")
                    return str(raw_value)
            
            # Si el valor ya es un string simple, lo devolvemos directamente
            print(f"✅ Valor simple encontrado para entity {entity_id}: '{raw_value}'")
            return raw_value
            
        except EntityValue.DoesNotExist:
            print(f"❌ No se encontró valor para entity {entity_id}")
            return None
        except Exception as e:
            print(f"❌ Error obteniendo valor de entity {entity_id}: {e}")
            return None
            
    def get_collected_entities_debug(self):
        """
        Función de debug para mostrar todas las entidades recolectadas con sus valores.
        """
        try:
            entity_values = EntityValue.objects.filter(
                sender_id=self.sender_id,
                team=self.team
            ).select_related('entity')
            
            result = {}
            for ev in entity_values:
                raw_value = ev.value
                processed_value = None
                
                # Extraer valor procesado si es un diccionario
                if isinstance(raw_value, dict):
                    processed_value = raw_value.get('processed', raw_value.get('raw', str(raw_value)))
                else:
                    processed_value = raw_value
                    
                result[ev.entity_id] = {
                    'raw_value': raw_value,
                    'processed_value': processed_value,
                    'entity_name': getattr(ev.entity, 'name', f'Entity {ev.entity_id}'),
                    'created_at': ev.created_at
                }
            
            return result
        except Exception as e:
            print(f"❌ Error en debug de entidades: {e}")
            return {}

"""
    def finish_session(self):
    def get_next_node(self, user_message=None):
    def evaluate_condition(self, condition, message_text=None):
    def _evaluate_single_condition(self, c, message_text=None):  
    def _evaluate_entity_condition(self, c):
    def _evaluate_message_condition(self, c, message_text=None):
    def _get_last_user_message(self):
    def get_collected_entity_ids(self):
    def get_entity_value(self, entity_id):
    def get_collected_entities_debug(self):
"""

class Path(models.Model):
    node = models.ForeignKey(Node, related_name="paths", on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    condition = models.JSONField(blank=True, null=True, help_text="Expresión JSONLogic o DSL")
    target_node = models.ForeignKey(Node, null=True, blank=True, on_delete=models.SET_NULL, related_name="incoming_paths")
    order = models.IntegerField(default=0)
    temporary_hide_on_message = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.label} -> {self.target_node_id or 'END'}"