from rest_framework import serializers
from .models import Team, TeamMember, Invitation
from django.contrib.auth import get_user_model
from apps.usuarios.serializers import PersonaSerializer

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    persona = PersonaSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ('id_usuario', 'nombre_usuario', 'email', 'phone', 'persona')
        read_only_fields = ('id_usuario',)

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ('id', 'name', 'slug', 'description', 'created_at')
        read_only_fields = ('created_at', 'slug')

class TeamMemberSerializer(serializers.ModelSerializer):
    # Campos derivados
    nombre = serializers.CharField(source='user.persona.nombre', read_only=True)
    apellido = serializers.CharField(source='user.persona.apellido', read_only=True)
    email = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()

    class Meta:
        model = TeamMember
        # Incluimos los campos públicos + los privados condicionales
        fields = ('id', 'user', 'team', 'nombre', 'apellido', 'email', 'telefono', 'role', 'joined_at')
        read_only_fields = ('id', 'joined_at')

    def get_email(self, obj):
        """Devuelve email solo si el usuario está autenticado."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user.email
        return None  # público → no se muestra

    def get_telefono(self, obj):
        """Devuelve teléfono solo si el usuario está autenticado."""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user.phone
        return None

class InvitationSerializer(serializers.ModelSerializer):
    # Utiliza TeamSerializer para obtener todos los detalles del equipo
    team = TeamSerializer(read_only=True)
    
    # Añade información sobre el creador de la invitación
    created_by = UserSerializer(read_only=True)
    
    # Campo adicional para permitir enviar solo el ID al crear/actualizar
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        source='team',
        write_only=True
    )
    
    class Meta:
        model = Invitation
        fields = ('id', 'team', 'team_id', 'email', 'phone', 'status', 'created_at', 'created_by')
        read_only_fields = ('id', 'created_at', 'status')
    
    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Se requiere email o teléfono.")
        
        if data.get('email') and data.get('phone'):
            raise serializers.ValidationError("Debe proporcionar solo email o teléfono, no ambos.")
            
        return data

class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False, max_length=20)
    
    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Se requiere email o teléfono.")
        
        if data.get('email') and data.get('phone'):
            raise serializers.ValidationError("Debe proporcionar solo email o teléfono, no ambos.")
            
        return data