from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from .models import Archivo, AccesoArchivo
from apps.teams.models import Team
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import (
    ArchivoSerializer, ArchivoListSerializer, ArchivoCreateSerializer,
    AccesoArchivoSerializer
)


class IsTeamMember(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action != "create":
            return True

        team_id = request.data.get("team")
        if not team_id:
            return False

        return Team.objects.filter(
            id=team_id,
            members__user=request.user
        ).exists()

    def has_object_permission(self, request, view, obj):
        return obj.team.members.filter(user=request.user).exists()


class ArchivoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de archivos"""
    permission_classes = [permissions.IsAuthenticated, IsTeamMember]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        if self.action == 'list':
            return ArchivoListSerializer
        elif self.action == 'create':
            return ArchivoCreateSerializer
        return ArchivoSerializer

    def get_queryset(self):
        """Filtrar archivos por teams del usuario"""
        return Archivo.objects.filter(
            team__members__user=self.request.user
        ).select_related('team', 'subido_por').distinct()

    def perform_create(self, serializer):
        """Registrar acceso al crear archivo"""
        archivo = serializer.save(subido_por=self.request.user)
        
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

    def perform_update(self, serializer):
        """Registrar acceso al actualizar archivo"""
        archivo = serializer.save()
        
        # Registrar modificación
        AccesoArchivo.objects.create(
            archivo=archivo,
            usuario=self.request.user,
            tipo_acceso='modificacion',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    def perform_destroy(self, instance):
        """Registrar acceso al eliminar archivo"""
        # Registrar eliminación ANTES de borrar
        AccesoArchivo.objects.create(
            archivo=instance,
            usuario=self.request.user,
            tipo_acceso='eliminacion',
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Eliminar el archivo físico de R2
        if instance.archivo:
            instance.archivo.delete(save=False)
        
        instance.delete()

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
            'url': archivo.archivo.url,  # R2 ya proporciona la URL completa
            'nombre': archivo.nombre,
            'tamano': archivo.tamano
        })

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtener historial de accesos del archivo"""
        archivo = self.get_object()
        accesos = archivo.accesos.select_related('usuario').all()
        serializer = AccesoArchivoSerializer(accesos, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """Buscar archivos por nombre o descripción"""
        query = request.query_params.get('q', '')
        tipo = request.query_params.get('tipo', '')
        team_id = request.query_params.get('team_id', '')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(nombre__icontains=query) | 
                Q(descripcion__icontains=query)
            )
        
        if tipo:
            queryset = queryset.filter(tipo_archivo=tipo)
        
        if team_id:
            queryset = queryset.filter(team_id=team_id)
        
        serializer = ArchivoListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def verificar_integridad(self, request, pk=None):
        """Verificar integridad del archivo mediante hash"""
        archivo = self.get_object()
        
        try:
            # Recalcular hash
            import hashlib
            sha256_hash = hashlib.sha256()
            
            # Abrir el archivo desde R2
            archivo.archivo.open('rb')
            for chunk in archivo.archivo.chunks():
                sha256_hash.update(chunk)
            archivo.archivo.close()
            
            hash_actual = sha256_hash.hexdigest()
            es_integro = hash_actual == archivo.hash_sha256
            
            return Response({
                'es_integro': es_integro,
                'hash_original': archivo.hash_sha256,
                'hash_actual': hash_actual,
                'fecha_verificacion': timezone.now()
            })
        except Exception as e:
            return Response({
                'error': f'Error al verificar integridad: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='subir-imagen')
    def subir_imagen(self, request):
        """Endpoint simplificado para subir imágenes y obtener URL"""
        archivo = request.FILES.get('imagen')
        team_id = request.data.get('team')
        
        if not archivo:
            return Response(
                {'error': 'Se requiere una imagen'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not team_id:
            return Response(
                {'error': 'Se requiere team_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el usuario pertenece al team
        from teams.models import Team
        try:
            team = Team.objects.get(id=team_id, members__user=request.user)
        except Team.DoesNotExist:
            return Response(
                {'error': 'No tienes acceso a este team'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Crear el archivo
        archivo_obj = Archivo.objects.create(
            team=team,
            nombre=request.data.get('nombre', archivo.name),
            descripcion=request.data.get('descripcion', ''),
            archivo=archivo,
            tipo_archivo='imagen',
            subido_por=request.user
        )
        
        # Registrar acceso
        AccesoArchivo.objects.create(
            archivo=archivo_obj,
            usuario=request.user,
            tipo_acceso='modificacion',
            ip_address=self.get_client_ip(),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'id': str(archivo_obj.id),
            'url': archivo_obj.archivo.url,  # URL pública de R2
            'nombre': archivo_obj.nombre,
            'tamano': archivo_obj.tamano
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de archivos del usuario"""
        queryset = self.get_queryset()
        
        total_archivos = queryset.count()
        total_tamano = sum(q.tamano or 0 for q in queryset)
        
        # Por tipo
        por_tipo = {}
        for tipo, _ in Archivo.TIPO_ARCHIVO_CHOICES:
            por_tipo[tipo] = queryset.filter(tipo_archivo=tipo).count()
        
        return Response({
            'total_archivos': total_archivos,
            'total_tamano_bytes': total_tamano,
            'total_tamano_mb': round(total_tamano / (1024 * 1024), 2),
            'por_tipo': por_tipo,
            'archivos_subidos_por_usuario': queryset.filter(subido_por=request.user).count()
        })

    def get_client_ip(self):
        """Obtener IP del cliente"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class AccesoArchivoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consultar historial de accesos"""
    serializer_class = AccesoArchivoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar accesos por archivos de los teams del usuario"""
        return AccesoArchivo.objects.filter(
            archivo__team__members__user=self.request.user
        ).select_related('archivo', 'usuario', 'archivo__team').distinct()

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
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas de accesos"""
        queryset = self.get_queryset()
        
        # Por tipo de acceso
        por_tipo = {}
        for tipo, _ in AccesoArchivo.TIPO_ACCESO_CHOICES:
            por_tipo[tipo] = queryset.filter(tipo_acceso=tipo).count()
        
        # Archivos más accedidos
        from django.db.models import Count
        mas_accedidos = queryset.values('archivo__nombre').annotate(
            total=Count('id')
        ).order_by('-total')[:10]
        
        return Response({
            'total_accesos': queryset.count(),
            'por_tipo': por_tipo,
            'archivos_mas_accedidos': list(mas_accedidos)
        })