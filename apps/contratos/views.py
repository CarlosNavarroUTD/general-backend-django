from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from PIL import Image
import io
import base64
import hashlib
from datetime import timedelta
import random
import string

from .models import (
    Contrato, CampoContrato, FirmanteContrato,
    HistorialContrato, CertificadoFirma
)
from .serializers import (
    ContratoSerializer, ContratoListSerializer, ContratoCreateSerializer,
    CampoContratoSerializer, FirmanteContratoSerializer,
    HistorialContratoSerializer, CertificadoFirmaSerializer,
    FirmaSerializer, FormularioDatosSerializer, VerificarCertificadoSerializer,
    CampoContratoUpdateSerializer, FirmanteContratoCreateSerializer
)


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_client_ip_from_request(request):
    """Obtener IP del cliente desde el request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def enviar_email_invitacion(firmante):
    """Enviar email de invitación al firmante"""
    url_formulario = f"{settings.FRONTEND_URL}/contratos/formulario/{firmante.contrato.token_formulario}?firmante={firmante.token_acceso}"
    
    asunto = f"Invitación para firmar: {firmante.contrato.titulo}"
    mensaje = f"""
    Hola {firmante.nombre_completo},
    
    Has sido invitado a firmar el contrato "{firmante.contrato.titulo}".
    
    Por favor, completa el formulario en el siguiente enlace:
    {url_formulario}
    
    Este enlace es personal e intransferible.
    
    Saludos,
    {firmante.contrato.team.nombre}
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [firmante.email],
            fail_silently=False,
        )
        
        firmante.fecha_invitacion_enviada = timezone.now()
        firmante.save()
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=firmante.contrato,
            tipo_accion='envio_email',
            descripcion=f"Email de invitación enviado a {firmante.email}",
            firmante=firmante
        )
    except Exception as e:
        print(f"Error enviando email: {e}")


def enviar_notificacion_firma(contrato, campo, firmante):
    """Enviar notificación cuando se firma un campo"""
    if not contrato.email_notificacion:
        return
    
    asunto = f"Nueva firma en contrato: {contrato.titulo}"
    mensaje = f"""
    Se ha firmado el campo "{campo.etiqueta}" del contrato "{contrato.titulo}".
    
    Firmante: {firmante.nombre_completo if firmante else 'Desconocido'}
    Fecha: {timezone.now()}
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [contrato.email_notificacion],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Error enviando notificación: {e}")


# ============================================================================
# PERMISOS PERSONALIZADOS
# ============================================================================

class IsTeamMember(permissions.BasePermission):
    """Permiso personalizado para verificar que el usuario pertenece al team"""
    
    def has_object_permission(self, request, view, obj):
        return obj.team.members.filter(id=request.user.id).exists()


# ============================================================================
# VIEWSETS AUTENTICADOS
# ============================================================================

class ContratoViewSet(viewsets.ModelViewSet):
    """ViewSet principal para gestión de contratos"""
    permission_classes = [permissions.IsAuthenticated, IsTeamMember]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContratoListSerializer
        elif self.action == 'create':
            return ContratoCreateSerializer
        return ContratoSerializer

    def get_queryset(self):
        """Filtrar contratos por teams del usuario"""
        user = self.request.user
        user_teams = user.teams.all()
        return Contrato.objects.filter(team__in=user_teams).select_related(
            'team', 'creado_por'
        ).prefetch_related('campos', 'firmantes')

    def perform_create(self, serializer):
        """Crear contrato y registrar en historial"""
        contrato = serializer.save()
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='creacion',
            descripcion=f"Contrato '{contrato.titulo}' creado",
            usuario=self.request.user,
            ip_address=get_client_ip_from_request(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """Activar un contrato para que pueda ser firmado"""
        contrato = self.get_object()
        
        if contrato.estado != 'borrador':
            return Response(
                {'error': 'Solo se pueden activar contratos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que tenga al menos un campo de firma
        if not contrato.campos.filter(tipo_campo='firma').exists():
            return Response(
                {'error': 'El contrato debe tener al menos un campo de firma'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contrato.estado = 'activo'
        contrato.fecha_activacion = timezone.now()
        contrato.save()
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='activacion',
            descripcion='Contrato activado',
            usuario=request.user,
            ip_address=get_client_ip_from_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = self.get_serializer(contrato)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar un contrato"""
        contrato = self.get_object()
        
        if contrato.estado == 'completado':
            return Response(
                {'error': 'No se puede cancelar un contrato completado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contrato.estado = 'cancelado'
        contrato.save()
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='cancelacion',
            descripcion='Contrato cancelado',
            usuario=request.user,
            ip_address=get_client_ip_from_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        serializer = self.get_serializer(contrato)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def agregar_campo(self, request, pk=None):
        """Agregar un campo al contrato"""
        contrato = self.get_object()
        
        if contrato.estado != 'borrador':
            return Response(
                {'error': 'Solo se pueden agregar campos a contratos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CampoContratoSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(contrato=contrato)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def agregar_firmante(self, request, pk=None):
        """Agregar un firmante al contrato"""
        contrato = self.get_object()
        
        serializer = FirmanteContratoCreateSerializer(
            data=request.data,
            context={'contrato': contrato}
        )
        
        if serializer.is_valid():
            firmante = serializer.save(contrato=contrato)
            
            # Enviar email de invitación
            enviar_email_invitacion(firmante)
            
            # Registrar en historial
            HistorialContrato.objects.create(
                contrato=contrato,
                tipo_accion='modificacion',
                descripcion=f"Firmante '{firmante.nombre_completo}' agregado",
                usuario=request.user,
                firmante=firmante,
                ip_address=get_client_ip_from_request(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response(
                FirmanteContratoSerializer(firmante).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def historial(self, request, pk=None):
        """Obtener historial del contrato"""
        contrato = self.get_object()
        historial = contrato.historial.all()
        serializer = HistorialContratoSerializer(historial, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def certificados(self, request, pk=None):
        """Obtener certificados de firma del contrato"""
        contrato = self.get_object()
        certificados = contrato.certificados.all()
        serializer = CertificadoFirmaSerializer(
            certificados,
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reenviar_invitacion(self, request, pk=None):
        """Reenviar invitación a un firmante"""
        contrato = self.get_object()
        firmante_id = request.data.get('firmante_id')
        
        if not firmante_id:
            return Response(
                {'error': 'Se requiere firmante_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        firmante = get_object_or_404(FirmanteContrato, id=firmante_id, contrato=contrato)
        
        # Reenviar email
        enviar_email_invitacion(firmante)
        
        return Response({'mensaje': 'Invitación reenviada correctamente'})


class CampoContratoViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de campos de contrato"""
    serializer_class = CampoContratoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar campos por contratos de los teams del usuario"""
        user = self.request.user
        user_teams = user.teams.all()
        return CampoContrato.objects.filter(
            contrato__team__in=user_teams
        ).select_related('contrato')

    @action(detail=True, methods=['patch'])
    def actualizar_valor(self, request, pk=None):
        """Actualizar el valor de un campo"""
        campo = self.get_object()
        serializer = CampoContratoUpdateSerializer(campo, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HistorialContratoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para historial de contratos"""
    serializer_class = HistorialContratoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar historial por contratos de los teams del usuario"""
        user = self.request.user
        user_teams = user.teams.all()
        return HistorialContrato.objects.filter(
            contrato__team__in=user_teams
        ).select_related('contrato', 'usuario', 'firmante')


class CertificadoFirmaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para certificados de firma"""
    serializer_class = CertificadoFirmaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar certificados por contratos de los teams del usuario"""
        user = self.request.user
        user_teams = user.teams.all()
        return CertificadoFirma.objects.filter(
            contrato__team__in=user_teams
        ).select_related('contrato', 'firmante')

    @action(detail=False, methods=['post'])
    def verificar(self, request):
        """Verificar la validez de un certificado por su hash"""
        serializer = VerificarCertificadoSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        hash_certificado = serializer.validated_data['hash_certificado']
        
        try:
            certificado = CertificadoFirma.objects.get(hash_certificado=hash_certificado)
            es_valido = certificado.verificar_integridad()
            
            return Response({
                'es_valido': es_valido,
                'certificado': CertificadoFirmaSerializer(certificado, context={'request': request}).data
            })
        except CertificadoFirma.DoesNotExist:
            return Response(
                {'error': 'Certificado no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# VISTAS PÚBLICAS (SIN AUTENTICACIÓN)
# ============================================================================

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def formulario_contrato(request, token):
    """
    Vista pública para el formulario de datos del contrato
    GET: Obtener información del contrato y campos a llenar
    POST: Enviar datos del formulario
    """
    contrato = get_object_or_404(Contrato, token_formulario=token)
    
    # Verificar que el contrato esté activo
    if not contrato.puede_firmar():
        return Response(
            {'error': 'Este contrato no está disponible para firmar'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar IP permitidas
    if contrato.ip_permitidas:
        client_ip = get_client_ip_from_request(request)
        ips_permitidas = [ip.strip() for ip in contrato.ip_permitidas.split(',')]
        if client_ip not in ips_permitidas:
            return Response(
                {'error': 'Acceso no autorizado desde esta IP'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    if request.method == 'GET':
        # Obtener campos que no son firma
        campos = contrato.campos.exclude(tipo_campo='firma').order_by('orden')
        campos_serializados = CampoContratoSerializer(campos, many=True).data
        
        # Registrar visualización
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='visualizacion',
            descripcion='Formulario visualizado',
            ip_address=get_client_ip_from_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'contrato': {
                'id': str(contrato.id),
                'titulo': contrato.titulo,
                'descripcion': contrato.descripcion,
                'fecha_expiracion': contrato.fecha_expiracion,
                'requiere_autenticacion_doble': contrato.requiere_autenticacion_doble
            },
            'campos': campos_serializados
        })
    
    elif request.method == 'POST':
        # Validar y guardar datos del formulario
        serializer = FormularioDatosSerializer(
            data=request.data,
            context={'contrato': contrato}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        datos = serializer.validated_data['datos']
        
        # Actualizar campos con los datos
        with transaction.atomic():
            for nombre_campo, valor in datos.items():
                try:
                    campo = contrato.campos.get(nombre_campo=nombre_campo)
                    campo.valor = valor
                    campo.save()
                except CampoContrato.DoesNotExist:
                    pass
            
            # Registrar en historial
            HistorialContrato.objects.create(
                contrato=contrato,
                tipo_accion='modificacion',
                descripcion='Formulario de datos completado',
                datos_adicionales={'datos': datos},
                ip_address=get_client_ip_from_request(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        # Generar URL para visualización y firma
        url_visualizacion = f"{settings.FRONTEND_URL}/contratos/ver/{contrato.token_visualizacion}"
        
        return Response({
            'mensaje': 'Datos guardados correctamente',
            'url_visualizacion': url_visualizacion,
            'token_visualizacion': contrato.token_visualizacion
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def ver_contrato(request, token):
    """
    Vista pública para visualizar el contrato y firmar
    """
    contrato = get_object_or_404(Contrato, token_visualizacion=token)
    
    # Verificar que el contrato esté activo
    if not contrato.puede_firmar():
        return Response(
            {'error': 'Este contrato no está disponible para firmar'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar IP permitidas
    if contrato.ip_permitidas:
        client_ip = get_client_ip_from_request(request)
        ips_permitidas = [ip.strip() for ip in contrato.ip_permitidas.split(',')]
        if client_ip not in ips_permitidas:
            return Response(
                {'error': 'Acceso no autorizado desde esta IP'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Obtener todos los campos
    campos = contrato.campos.all().order_by('pagina', 'orden')
    campos_serializados = CampoContratoSerializer(campos, many=True).data
    
    # Registrar visualización
    HistorialContrato.objects.create(
        contrato=contrato,
        tipo_accion='visualizacion',
        descripcion='Contrato visualizado para firma',
        ip_address=get_client_ip_from_request(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return Response({
        'contrato': {
            'id': str(contrato.id),
            'titulo': contrato.titulo,
            'descripcion': contrato.descripcion,
            'documento_url': request.build_absolute_uri(contrato.documento_original.url),
            'campos': campos_serializados,
            'estado': contrato.estado,
            'todas_firmas_completadas': contrato.todas_firmas_completadas()
        }
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def firmar_campo(request, token):
    """
    Vista pública para firmar un campo específico
    """
    contrato = get_object_or_404(Contrato, token_visualizacion=token)
    
    # Verificar que el contrato esté activo
    if not contrato.puede_firmar():
        return Response(
            {'error': 'Este contrato no está disponible para firmar'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = FirmaSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    campo_id = serializer.validated_data['campo_id']
    firma_base64 = serializer.validated_data['firma_base64']
    
    # Obtener el campo
    campo = get_object_or_404(CampoContrato, id=campo_id, contrato=contrato)
    
    if campo.tipo_campo != 'firma':
        return Response(
            {'error': 'Este campo no es de tipo firma'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if campo.firmado:
        return Response(
            {'error': 'Este campo ya ha sido firmado'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Procesar la firma base64
        format, imgstr = firma_base64.split(';base64,')
        ext = format.split('/')[-1]
        
        # Decodificar y guardar la imagen
        image_data = base64.b64decode(imgstr)
        image = Image.open(io.BytesIO(image_data))
        
        # Guardar la firma
        from django.core.files.base import ContentFile
        campo.firma_imagen.save(
            f'firma_{campo.id}.{ext}',
            ContentFile(image_data),
            save=False
        )
        
        # Marcar como firmado
        campo.firmado = True
        campo.fecha_firma = timezone.now()
        campo.ip_firma = get_client_ip_from_request(request)
        campo.save()
        
        # Buscar firmante asociado (por email en los datos)
        email_campo = contrato.campos.filter(tipo_campo='email').first()
        firmante = None
        if email_campo and email_campo.valor:
            firmante = contrato.firmantes.filter(email=email_campo.valor).first()
            if firmante:
                firmante.estado = 'completado'
                firmante.fecha_completado = timezone.now()
                firmante.ip_address = get_client_ip_from_request(request)
                firmante.user_agent = request.META.get('HTTP_USER_AGENT', '')
                firmante.save()
        
        # Si no hay firmante, usar el primero disponible
        if not firmante:
            firmante = contrato.firmantes.first()
        
        # Crear certificado de firma
        certificado = CertificadoFirma.objects.create(
            contrato=contrato,
            firmante=firmante,
            hash_documento=contrato.hash_documento_original,
            hash_firma=campo.firma_hash,
            ip_address=get_client_ip_from_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='firma',
            descripcion=f'Campo "{campo.etiqueta}" firmado',
            firmante=firmante,
            datos_adicionales={
                'campo_id': str(campo.id),
                'certificado_id': str(certificado.id)
            },
            ip_address=get_client_ip_from_request(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Enviar notificación si está configurado
        if contrato.notificar_cada_firma and contrato.email_notificacion:
            enviar_notificacion_firma(contrato, campo, firmante)
        
        # Verificar si todas las firmas están completadas
        if contrato.todas_firmas_completadas():
            contrato.estado = 'completado'
            contrato.fecha_completado = timezone.now()
            contrato.save()
            
            # Generar documento firmado (aquí iría la lógica para aplicar las firmas al PDF)
            # TODO: Implementar generación de PDF con firmas
            
            HistorialContrato.objects.create(
                contrato=contrato,
                tipo_accion='completado',
                descripcion='Contrato completado - todas las firmas aplicadas',
                ip_address=get_client_ip_from_request(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return Response({
            'mensaje': 'Firma guardada correctamente',
            'campo': CampoContratoSerializer(campo).data,
            'certificado': CertificadoFirmaSerializer(certificado).data,
            'contrato_completado': contrato.todas_firmas_completadas()
        })
        
    except Exception as e:
        return Response(
            {'error': f'Error procesando la firma: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_codigo_verificacion(request, token):
    """
    Solicitar código de verificación por email
    """
    contrato = get_object_or_404(Contrato, token_visualizacion=token)
    
    if not contrato.requiere_autenticacion_doble:
        return Response(
            {'error': 'Este contrato no requiere autenticación doble'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    email = request.data.get('email')
    if not email:
        return Response(
            {'error': 'Se requiere un email'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Buscar firmante
    firmante = get_object_or_404(FirmanteContrato, contrato=contrato, email=email)
    
    # Generar código de 6 dígitos
    codigo = ''.join(random.choices(string.digits, k=6))
    
    firmante.codigo_verificacion = codigo
    firmante.codigo_verificacion_expira = timezone.now() + timedelta(minutes=10)
    firmante.intentos_verificacion = 0
    firmante.save()
    
    # Enviar email con código
    asunto = f"Código de verificación - {contrato.titulo}"
    mensaje = f"""
    Hola {firmante.nombre_completo},
    
    Tu código de verificación es: {codigo}
    
    Este código expira en 10 minutos.
    
    Si no solicitaste este código, ignora este mensaje.
    """
    
    try:
        send_mail(
            asunto,
            mensaje,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        
        # Registrar en historial
        HistorialContrato.objects.create(
            contrato=contrato,
            tipo_accion='envio_email',
            descripcion=f'Código de verificación enviado a {email}',
            firmante=firmante
        )
        
        return Response({'mensaje': 'Código enviado correctamente'})
    except Exception as e:
        return Response(
            {'error': 'Error enviando el código'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verificar_codigo(request, token):
    """
    Verificar código de autenticación
    """
    contrato = get_object_or_404(Contrato, token_visualizacion=token)
    
    email = request.data.get('email')
    codigo = request.data.get('codigo')
    
    if not email or not codigo:
        return Response(
            {'error': 'Se requiere email y código'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    firmante = get_object_or_404(FirmanteContrato, contrato=contrato, email=email)
    
    # Verificar intentos
    if firmante.intentos_verificacion >= contrato.limite_intentos_firma:
        return Response(
            {'error': 'Límite de intentos excedido'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Verificar expiración
    if firmante.codigo_verificacion_expira and timezone.now() > firmante.codigo_verificacion_expira:
        return Response(
            {'error': 'El código ha expirado'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar código
    if firmante.codigo_verificacion != codigo:
        firmante.intentos_verificacion += 1
        firmante.save()
        
        return Response(
            {'error': 'Código incorrecto', 'intentos_restantes': contrato.limite_intentos_firma - firmante.intentos_verificacion},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Código correcto
    firmante.intentos_verificacion = 0
    firmante.codigo_verificacion = ''
    firmante.codigo_verificacion_expira = None
    firmante.save()
    
    # Registrar en historial
    HistorialContrato.objects.create(
        contrato=contrato,
        tipo_accion='verificacion',
        descripcion=f'Código verificado correctamente para {email}',
        firmante=firmante,
        ip_address=get_client_ip_from_request(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return Response({
        'mensaje': 'Código verificado correctamente',
        'verificado': True
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def descargar_certificado(request, hash_certificado):
    """
    Descargar un certificado de firma en formato JSON
    """
    return ('Thiswork')