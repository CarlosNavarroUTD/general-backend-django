# apps/integraciones/serializers.py

from rest_framework import serializers
from .models import GoogleToken, GoogleMapsIntegration, GooglePlaceBusiness, WhatsappInstance, GoogleSheetIntegration

class GoogleMapsIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleMapsIntegration
        fields = ['id', 'team', 'place_id', 'activo', 'creado_en', 'actualizado_en']
        read_only_fields = ['creado_en', 'actualizado_en']


class GoogleTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleToken
        fields = ['access_token', 'refresh_token', 'expires_at']
        read_only_fields = ['expires_at']


class GooglePlaceBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = GooglePlaceBusiness
        fields = [
            'id',
            'team',
            'name',
            'place_id',
            'address',
            'phone',
            'website',
            'rating',
            'user_ratings_total',
            'business_status',
            'activo',
            'creado_en',
            'actualizado_en'
        ]
        read_only_fields = ['creado_en', 'actualizado_en']

class WhatsappInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsappInstance
        fields = [
            'id',
            'team',
            'instance_name',
            'instance_id',
            'token',
            'status',
            'phone_number',
            'activo',
            'creado_en',
            'actualizado_en'
        ]
        read_only_fields = ['instance_id', 'token', 'status', 'creado_en', 'actualizado_en']
class GoogleSheetIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleSheetIntegration
        fields = [
            'id', 'team', 'spreadsheet_id', 'sheet_name', 'entidad',
            'mapping', 'identificadores', 'last_sync', 'activo',
            'creado_en', 'actualizado_en'
        ]
        read_only_fields = ['last_sync', 'creado_en', 'actualizado_en']
