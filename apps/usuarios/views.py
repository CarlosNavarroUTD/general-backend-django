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

from .models import Usuario, Persona, DocumentoUsuario, ActividadUsuario
from .serializers import UsuarioSerializer, PersonaSerializer, DocumentoSerializer, ActividadUsuarioSerializer

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
    
    @action(detail=True, methods=['get', 'post'])
    def documentos(self, request, pk=None):
        """
        GET /api/usuarios/{id}/documentos/ - Listar documentos
        POST /api/usuarios/{id}/documentos/ - Subir documentos
        """
        usuario = self.get_object()
        
        if request.method == 'GET':
            documentos = usuario.documentos.order_by('-fecha_subida')
            serializer = DocumentoSerializer(
                documentos, 
                many=True,
                context={'request': request}
            )
            return Response(serializer.data)
        
        elif request.method == 'POST':
            # Manejar múltiples archivos
            archivos = request.FILES.getlist('documentos')
            if not archivos:
                return Response(
                    {'error': 'No se proporcionaron archivos'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            documentos_creados = []
            errores = []
            
            for archivo in archivos:
                try:
                    # Crear documento
                    documento = DocumentoUsuario.objects.create(
                        usuario=usuario,
                        nombre_original=archivo.name,
                        archivo=archivo,
                        tipo_documento=request.data.get('tipo_documento', 'OTRO'),
                        descripcion=request.data.get('descripcion', '')
                    )
                    
                    documentos_creados.append(documento)
                    
                    # Registrar actividad
                    ActividadUsuario.objects.create(
                        usuario=usuario,
                        tipo_actividad='DOCUMENTO_SUBIDO',
                        descripcion=f'Documento subido: {archivo.name}'
                    )
                    
                except Exception as e:
                    errores.append({
                        'archivo': archivo.name,
                        'error': str(e)
                    })
            
            # Serializar documentos creados
            serializer = DocumentoSerializer(
                documentos_creados,
                many=True,
                context={'request': request}
            )
            
            response_data = {
                'documentos': serializer.data,
                'total_creados': len(documentos_creados),
            }
            
            if errores:
                response_data['errores'] = errores
                response_data['total_errores'] = len(errores)
            
            return Response(
                response_data,
                status=status.HTTP_201_CREATED if documentos_creados else status.HTTP_400_BAD_REQUEST
            )

class PersonaViewSet(viewsets.ModelViewSet):
    queryset = Persona.objects.all()
    serializer_class = PersonaSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Persona.objects.all()
        return Persona.objects.filter(usuario=self.request.user)

class DocumentoViewSet(viewsets.ModelViewSet):
    queryset = DocumentoUsuario.objects.all()
    serializer_class = DocumentoSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        usuario_id = self.request.query_params.get('usuario_id')
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return queryset.order_by('-fecha_subida')
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /api/documentos/{id}/"""
        documento = self.get_object()
        usuario = documento.usuario
        nombre = documento.nombre
        
        # Eliminar archivo físico
        if documento.archivo:
            documento.archivo.delete(save=False)
        
        # Registrar actividad usando TUS campos originales
        ActividadUsuario.objects.create(
            usuario=usuario,
            tipo='DOCUMENTO_SUBIDO',  # Cambia esto si tienes 'DOCUMENTO_ELIMINADO'
            descripcion=f'Documento eliminado: {nombre}'
        )
        
        documento.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

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

