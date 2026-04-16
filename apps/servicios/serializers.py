# apps/servicios/serializers.py
from rest_framework import serializers
from .models import Servicio, CampoPersonalizado, ServicioCampoValor


# ──────────────────────────────────────────────
# CampoPersonalizado (definición del campo)
# ──────────────────────────────────────────────

class CampoPersonalizadoSerializer(serializers.ModelSerializer):
    """CRUD completo para las definiciones de campos personalizados de un team."""

    class Meta:
        model = CampoPersonalizado
        fields = ['id', 'personalizado_id', 'nombre', 'tipo', 'requerido', 'team']
        read_only_fields = ['personalizado_id']


# ──────────────────────────────────────────────
# ServicioCampoValor (lectura)
# ──────────────────────────────────────────────

class ServicioCampoValorReadSerializer(serializers.ModelSerializer):
    """
    Serializer de LECTURA para los valores de campos de un servicio.
    Expone información legible del campo y su valor.
    """
    campo_id = serializers.IntegerField(source='campo.id', read_only=True)
    campo_nombre = serializers.CharField(source='campo.nombre', read_only=True)
    campo_tipo = serializers.CharField(source='campo.tipo', read_only=True)
    campo_requerido = serializers.BooleanField(source='campo.requerido', read_only=True)
    valor = serializers.SerializerMethodField()

    class Meta:
        model = ServicioCampoValor
        fields = ['id', 'campo_id', 'campo_nombre', 'campo_tipo', 'campo_requerido', 'valor']

    def get_valor(self, obj):
        return obj.valor


# ──────────────────────────────────────────────
# ServicioCampoValor (escritura — campo anidado)
# ──────────────────────────────────────────────

class ServicioCampoValorWriteSerializer(serializers.Serializer):
    """
    Serializer de ESCRITURA para recibir valores de campos dentro
    del JSON de creación/actualización de un Servicio.

    Ejemplo de entrada:
        { "campo": 3, "valor": "Consulta inicial" }
        { "campo": 5, "valor": 90.5 }
        { "campo": 7, "valor": true }
        { "campo": 9, "valor": "2025-06-01" }
    """
    campo = serializers.PrimaryKeyRelatedField(queryset=CampoPersonalizado.objects.all())
    valor = serializers.JSONField()

    def validate(self, data):
        campo = data['campo']
        valor = data['valor']
        tipo = campo.tipo

        # Validación de tipo de dato según la definición del campo
        type_map = {
            CampoPersonalizado.TIPO_TEXTO: str,
            CampoPersonalizado.TIPO_NUMERO: (int, float),
            CampoPersonalizado.TIPO_BOOLEANO: bool,
        }

        if tipo in type_map and not isinstance(valor, type_map[tipo]):
            tipo_legible = dict(CampoPersonalizado.TIPOS).get(tipo, tipo)
            raise serializers.ValidationError(
                {campo.nombre: f"Se esperaba un valor de tipo '{tipo_legible}'."}
            )

        if tipo == CampoPersonalizado.TIPO_FECHA:
            # Validar formato de fecha YYYY-MM-DD
            from datetime import date
            try:
                if not isinstance(valor, str):
                    raise ValueError
                year, month, day = valor.split('-')
                date(int(year), int(month), int(day))
            except (ValueError, AttributeError):
                raise serializers.ValidationError(
                    {campo.nombre: "La fecha debe tener el formato YYYY-MM-DD."}
                )

        return data


# ──────────────────────────────────────────────
# Servicio — uso interno (autenticado)
# ──────────────────────────────────────────────

class ServicioSerializer(serializers.ModelSerializer):
    """
    Serializer completo para uso interno.

    - Lectura  → campos_valores: lista de valores existentes con detalle del campo.
    - Escritura → campos_input: lista de { campo, valor } para crear/reemplazar valores.

    Ejemplo de JSON para crear un servicio con campos:
    {
        "nombre": "Corte de cabello",
        "descripcion": "Servicio básico",
        "precio": 150.00,
        "duracion": 45,
        "team": 1,
        "campos_input": [
            { "campo": 3, "valor": "Técnica clásica" },
            { "campo": 5, "valor": 120 }
        ]
    }
    """
    # Solo lectura: campos ya guardados con detalle
    campos_valores = ServicioCampoValorReadSerializer(many=True, read_only=True)
    # Solo escritura: campos a guardar en create/update
    campos_input = ServicioCampoValorWriteSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Servicio
        fields = [
            'id',
            'team',
            'nombre',
            'descripcion',
            'precio',
            'duracion',
            'activo',
            'fecha_creacion',
            'url_img',
            'campos_valores',   # salida
            'campos_input',     # entrada
        ]
        read_only_fields = ['fecha_creacion']

    def validate_campos_input(self, campos_input):
        """Verifica que no haya campos duplicados en la misma petición."""
        ids = [item['campo'].id for item in campos_input]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "No puedes enviar el mismo campo más de una vez."
            )
        return campos_input

    def create(self, validated_data):
        campos_input = validated_data.pop('campos_input', [])
        servicio = Servicio.objects.create(**validated_data)
        self._guardar_campos(servicio, campos_input)
        return servicio

    def update(self, instance, validated_data):
        campos_input = validated_data.pop('campos_input', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Si se envían campos en el update, se reemplazan todos
        if campos_input is not None:
            instance.campos_valores.all().delete()
            self._guardar_campos(instance, campos_input)

        return instance

    def _guardar_campos(self, servicio, campos_input):
        """Crea los objetos ServicioCampoValor para el servicio."""
        for item in campos_input:
            campo = item['campo']
            valor = item['valor']

            obj = ServicioCampoValor(servicio=servicio, campo=campo)

            if campo.tipo == CampoPersonalizado.TIPO_TEXTO:
                obj.valor_texto = valor
            elif campo.tipo == CampoPersonalizado.TIPO_NUMERO:
                obj.valor_numero = valor
            elif campo.tipo == CampoPersonalizado.TIPO_FECHA:
                obj.valor_fecha = valor
            elif campo.tipo == CampoPersonalizado.TIPO_BOOLEANO:
                obj.valor_booleano = valor

            obj.save()


# ──────────────────────────────────────────────
# Servicio — endpoint público
# ──────────────────────────────────────────────

class ServicioPublicoSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para el endpoint público.
    Incluye campos personalizados sin exponer info sensible.
    """
    duracion_formateada = serializers.SerializerMethodField()
    campos_valores = ServicioCampoValorReadSerializer(many=True, read_only=True)

    class Meta:
        model = Servicio
        fields = [
            'id',
            'nombre',
            'descripcion',
            'precio',
            'duracion',
            'duracion_formateada',
            'fecha_creacion',
            'url_img',
            'campos_valores',
        ]

    def get_duracion_formateada(self, obj):
        if obj.duracion < 60:
            return f"{obj.duracion} min"
        horas = obj.duracion // 60
        minutos = obj.duracion % 60
        if minutos == 0:
            return f"{horas}h"
        return f"{horas}h {minutos}min"