# apps/integraciones/serializers.py

from rest_framework import serializers
from .models import GoogleToken, GoogleMapsIntegration, GooglePlaceBusiness

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
