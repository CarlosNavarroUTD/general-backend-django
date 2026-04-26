# apps/campos/serializers.py

from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType

from apps.teams.models import Team
from .models import Campo, CampoValor


# ──────────────────────────────────────────
# Serializers de Campo (definición)
# ──────────────────────────────────────────

class CampoSerializer(serializers.ModelSerializer):
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        source='team',
        write_only=True
    )

    class Meta:
        model  = Campo
        fields = [
            'id', 'entidad', 'nombre', 'clave', 'tipo',
            'requerido', 'activo', 'opciones', 'orden', 'creado_en', 'team_id',
        ]
        read_only_fields = ['id', 'creado_en']

    def validate(self, data):
        tipo     = data.get('tipo', getattr(self.instance, 'tipo', None))
        opciones = data.get('opciones', getattr(self.instance, 'opciones', []))

        if tipo == 'seleccion' and not opciones:
            raise serializers.ValidationError(
                {'opciones': 'Debes definir opciones para campos de tipo selección.'}
            )
        return data


# ──────────────────────────────────────────
# Mixin reutilizable para CUALQUIER modelo
# ──────────────────────────────────────────

class CamposPersonalizadosMixin:
    """
    Agrega lectura/escritura de campos personalizados a cualquier serializer.

    Uso:
        class LeadSerializer(CamposPersonalizadosMixin, serializers.ModelSerializer):
            personalizados = serializers.JSONField(required=False, default=dict)
            ENTIDAD = 'lead'   ← obligatorio

    Payload esperado:
        { "nombre": "Juan", ..., "personalizados": { "prioridad": "Alta", "origen": "Web" } }
    """

    ENTIDAD = None  # Subclases deben sobreescribir esto

    def get_team(self):
        """
        Obtiene el team del contexto del request.
        Busca team_id en query params (GET) o en el body (POST/PUT).
        El permiso EsMiembroDelTeam ya garantizó que el usuario pertenece a él.
        """
        request = self.context.get('request')
        if not request:
            return None

        team_id = (
            request.query_params.get('team_id')
            or request.data.get('team_id')
            or request.data.get('team')
        )

        if not team_id:
            return None

        from apps.teams.models import Team
        return Team.objects.filter(pk=team_id).first()

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        # Leer valores guardados y exponerlos como dict {clave: valor}
        content_type = ContentType.objects.get_for_model(instance)
        valores = CampoValor.objects.filter(
            content_type=content_type,
            object_id=instance.pk,
        ).select_related('campo')

        rep['personalizados'] = {
            cv.campo.clave: cv.valor_tipado()
            for cv in valores
        }
        return rep

    def _guardar_personalizados(self, instance, personalizados: dict):
        if not personalizados:
            return

        team         = self.get_team()
        content_type = ContentType.objects.get_for_model(instance)

        # Traer los campos definidos para esta entidad+team de una sola query
        campos_map = {
            c.clave: c
            for c in Campo.objects.filter(
                team=team,
                entidad=self.ENTIDAD,
                activo=True,
            )
        }

        errores = {}
        for clave, valor in personalizados.items():
            campo = campos_map.get(clave)
            if not campo:
                errores[clave] = f"El campo '{clave}' no existe para esta entidad."
                continue

            # Validar opciones si es selección
            if campo.tipo == 'seleccion' and valor not in campo.opciones:
                errores[clave] = f"Valor inválido. Opciones: {campo.opciones}"
                continue

            # Upsert del valor
            CampoValor.objects.update_or_create(
                campo=campo,
                content_type=content_type,
                object_id=instance.pk,
                defaults={'valor': str(valor) if valor is not None else None},
            )

        if errores:
            raise serializers.ValidationError({'personalizados': errores})

    def _validar_requeridos(self, personalizados: dict):
        """Verifica campos requeridos antes de guardar."""
        team = self.get_team()
        campos_requeridos = Campo.objects.filter(
            team=team, entidad=self.ENTIDAD, activo=True, requerido=True
        )
        faltantes = [
            c.clave for c in campos_requeridos
            if c.clave not in personalizados or personalizados[c.clave] in (None, '')
        ]
        if faltantes:
            raise serializers.ValidationError(
                {'personalizados': {c: 'Este campo es requerido.' for c in faltantes}}
            )

    def create(self, validated_data):
        personalizados = validated_data.pop('personalizados', {})
        self._validar_requeridos(personalizados)
        instance = super().create(validated_data)
        self._guardar_personalizados(instance, personalizados)
        return instance

    def update(self, instance, validated_data):
        personalizados = validated_data.pop('personalizados', {})
        instance = super().update(instance, validated_data)
        self._guardar_personalizados(instance, personalizados)
        return instance