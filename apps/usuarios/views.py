# apps/usuarios/views.py
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from allauth.socialaccount.models import SocialAccount
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import urllib.parse
import requests
import json
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Allauth & Social Auth
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

from .models import Usuario, Persona, ActividadUsuario
from .serializers import UsuarioSerializer, PersonaSerializer, ActividadUsuarioSerializer

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Si el objeto tiene 'usuario' (Persona), comparar con el request.user
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user or request.user.is_staff
        # Si el objeto es un usuario directamente
        return obj == request.user or request.user.is_staff

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    lookup_field = 'pk'

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), IsOwnerOrAdmin()]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        # Enviar correo de confirmación manualmente usando allauth
        from allauth.account.utils import send_email_confirmation
        user = Usuario.objects.get(id_usuario=response.data.get('id_usuario') or response.data.get('id'))
        send_email_confirmation(request, user)
        return response

    def get_queryset(self):
        if self.request.user.is_staff:
            return Usuario.objects.all()
        return Usuario.objects.filter(id_usuario=self.request.user.id_usuario)

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='me')
    def me(self, request):
        if request.method in ['PUT', 'PATCH']:
            serializer = self.get_serializer(
                request.user, 
                data=request.data, 
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        else:  # GET
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def actividades(self, request, pk=None):
        """GET /api/usuarios/{id}/actividades/"""
        usuario = self.get_object()
        actividades = usuario.actividades.all()
        
        # Paginación opcional
        page = self.paginate_queryset(actividades)
        if page is not None:
            serializer = ActividadUsuarioSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ActividadUsuarioSerializer(actividades, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def agregar_actividad(self, request, pk=None):
        """POST /api/usuarios/{id}/agregar_actividad/"""
        usuario = self.get_object()
        
        data = request.data.copy()
        data['usuario'] = usuario.id_usuario
        
        serializer = ActividadUsuarioSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Persona.objects.all()
        return Persona.objects.filter(usuario=self.request.user)


# ========== VISTAS PARA TOKENS CON INFORMACIÓN DEL USUARIO ==========
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Agregar claims personalizados si lo deseas
        token['email'] = user.email
        return token
    
    def validate(self, attrs):
        # Debug: imprimir lo que llega
        print("🔍 Attrs recibidos:", attrs)
        
        # Obtener credenciales
        email = attrs.get('email') or attrs.get('username')  # Intentar ambos
        password = attrs.get('password')
        
        print(f"📧 Email extraído: {email}")
        print(f"🔑 Password presente: {bool(password)}")
        
        if not email or not password:
            raise serializers.ValidationError({
                "detail": "Debe proporcionar email y contraseña"
            })
        
        # Intentar autenticación
        from django.contrib.auth import authenticate
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        print(f"👤 Usuario autenticado: {user}")
        
        if not user:
            raise serializers.ValidationError({
                "detail": "Credenciales inválidas o usuario inactivo"
            })
        
        if not user.is_active:
            raise serializers.ValidationError({
                "detail": "Usuario inactivo"
            })
            
        # Verificar que el correo esté confirmado (Allauth)
        from allauth.account.models import EmailAddress
        email_address = EmailAddress.objects.filter(user=user, email__iexact=email).first()
        if not email_address or not email_address.verified:
            # Permit staff or superusers to bypass email verification (admin created accounts)
            if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
                # Optionally mark the email as verified to avoid future checks
                if email_address:
                    email_address.verified = True
                    email_address.save()
                # Continue without raising an error
                pass
            else:
                raise serializers.ValidationError({
                    "detail": "Debes verificar tu correo electrónico antes de iniciar sesión."
                })
            
        # Generar tokens
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UsuarioSerializer(user).data
        }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ========== VISTAS PARA GOOGLE AUTH (REST) ==========

class CustomOAuth2Client(OAuth2Client):
    """
    Parche para solucionar la incompatibilidad entre dj-rest-auth y allauth >= 0.60.
    dj-rest-auth v7 pasa 'scope' como argumento posicional #7, pero allauth v65+
    espera 'scope_delimiter' en esa posición. Esto causa 'multiple values'.
    Solución: capturar todos los args/kwargs y reconstruir la llamada limpiamente.
    """
    def __init__(self, request, consumer_key, consumer_secret, access_token_method,
                 access_token_url, callback_url, *args, **kwargs):
        # dj-rest-auth pasa: scope (positional), scope_delimiter, headers, basic_auth (kwargs)
        # allauth espera: scope_delimiter, headers, basic_auth (todos kwargs o por posición)
        # Solución: ignorar args (que contiene 'scope') y pasar solo los kwargs válidos
        super().__init__(
            request,
            consumer_key,
            consumer_secret,
            access_token_method,
            access_token_url,
            callback_url,
            scope_delimiter=kwargs.get('scope_delimiter', ' '),
            headers=kwargs.get('headers', None),
            basic_auth=kwargs.get('basic_auth', False),
        )

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    # "postmessage" es requerido por @react-oauth/google cuando usa flow: "auth-code" (popup)
    callback_url = "postmessage"
    client_class = CustomOAuth2Client

    def post(self, request, *args, **kwargs):
        print(f"🔍 GoogleLogin attempt with data: {request.data}")
        return super().post(request, *args, **kwargs)
