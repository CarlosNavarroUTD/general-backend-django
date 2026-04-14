from rest_framework import serializers
from .models import Portafolio

class PortafolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Portafolio
        fields = '__all__'