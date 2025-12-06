from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Archivo, AccesoArchivo
from .serializers import (
    ArchivoSerializer, ArchivoListSerializer, ArchivoCreateSerializer,
    AccesoArchivoSerializer, AccesoArchivoCreateSerializer
)


class IsTeamMember(permissions.BasePermission):
    """Permiso personalizado para verificar que el usuario pertenece al team"""
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es miembro del team
        return obj.team.members.filter(id=request.user.id).exists()


class ArchivoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de archivos"""
    permission_classes = [permissions.IsAuthenticated, IsTeamMember]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArchivoListSerializer
        elif self.action == 'create':
            return ArchivoCreateSerializer
        return ArchivoSerializer

    def get_queryset(self):
        """Filtrar archivos por teams del usuario"""
        user = self.request.user
        # Obtener todos los teams del usuario
        user_teams = user.teams.all()
        return Archivo.objects.filter(team__members__user=self.request.user)

    def perform_create(self, serializer):
        """Registrar acceso al crear archivo"""
        archivo = serializer.save()
        
        # Registrar en el historial
        AccesoArchivo.objects.create(
            archivo=archivo,
            usuario=self.request.user,
            tipo_acceso='modificacion',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    def retrieve(self, request, *args, **kwargs):
        """Registrar acceso al visualizar archivo"""
        instance = self.get_object()
        
        # Registrar visualización
        AccesoArchivo.objects.create(
            archivo=instance,
            usuario=request.user,
            tipo_acceso='visualizacion',
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def descargar(self, request, pk=None):
        """Registrar descarga de archivo"""
        archivo = self.get_object()
        
        # Registrar descarga
        AccesoArchivo.objects.create(
            archivo=archivo,
            usuario=request.user,
            tipo_acceso='descarga',
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'url': request.build_absolute_uri(archivo.archivo.url),
            'nombre': archivo.nombre,
            'tamano': archivo.tamano
        })

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtener historial de accesos del archivo"""
        archivo = self.get_object()
        accesos = archivo.accesos.all()
        serializer = AccesoArchivoSerializer(accesos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Buscar archivos por nombre o descripción"""
        query = request.query_params.get('q', '')
        tipo = request.query_params.get('tipo', '')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) | 
                Q(descripcion__icontains=query)
            )
        
        if tipo:
            queryset = queryset.filter(tipo_archivo=tipo)
        
        serializer = ArchivoListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def verificar_integridad(self, request, pk=None):
        """Verificar integridad del archivo mediante hash"""
        archivo = self.get_object()
        
        # Recalcular hash
        import hashlib
        sha256_hash = hashlib.sha256()
        for chunk in archivo.archivo.chunks():
            sha256_hash.update(chunk)
        hash_actual = sha256_hash.hexdigest()
        
        es_integro = hash_actual == archivo.hash_sha256
        
        return Response({
            'es_integro': es_integro,
            'hash_original': archivo.hash_sha256,
            'hash_actual': hash_actual,
            'fecha_verificacion': timezone.now()
        })

    def get_client_ip(self):
        """Obtener IP del cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class AccesoArchivoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar historial de accesos"""
    serializer_class = AccesoArchivoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar accesos por archivos de los teams del usuario"""
        user = self.request.user
        user_teams = user.teams.all()
        return AccesoArchivo.objects.filter(
            archivo__team__in=user_teams
        ).select_related('archivo', 'usuario')

    @action(detail=False, methods=['get'])
    def mis_accesos(self, request):
        """Obtener accesos del usuario actual"""
        accesos = self.get_queryset().filter(usuario=request.user)
        serializer = self.get_serializer(accesos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def por_archivo(self, request):
        """Obtener accesos de un archivo específico"""
        archivo_id = request.query_params.get('archivo_id')
        if not archivo_id:
            return Response(
                {'error': 'Se requiere archivo_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        accesos = self.get_queryset().filter(archivo_id=archivo_id)
        serializer = self.get_serializer(accesos, many=True)
        return Response(serializer.data)