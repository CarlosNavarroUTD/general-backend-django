# apps/conversaciones/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Conversacion, Message
from .serializers import (
    ConversacionListSerializer,
    ConversacionDetailSerializer,
    MessageSerializer,
    CreateMessageSerializer
)
from apps.teams.models import TeamMember

class ConversacionViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar conversaciones"""
    permission_classes = [IsAuthenticated]
    
    def get_user_team(self):
        """Obtiene el team del usuario autenticado"""
        try:
            # Obtener el primer team del usuario (puedes ajustar la lógica según tus necesidades)
            team_member = TeamMember.objects.filter(user=self.request.user).first()
            if team_member:
                return team_member.team
            return None
        except TeamMember.DoesNotExist:
            return None
    
    def get_queryset(self):
        # Obtener el team del usuario
        team = self.get_user_team()
        
        if not team:
            # Si el usuario no tiene team, retornar queryset vacío
            return Conversacion.objects.none()
        
        queryset = Conversacion.objects.filter(team=team)
        
        # Filtrar por sender_id si se proporciona
        sender_id = self.request.query_params.get('sender_id')
        if sender_id:
            queryset = queryset.filter(sender_id=sender_id)
        
        # Filtrar por status
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
        
        # Filtrar por plataforma
        platform = self.request.query_params.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        return queryset.select_related('lead', 'assigned_to').prefetch_related('messages')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversacionDetailSerializer
        return ConversacionListSerializer
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Obtener todos los mensajes de una conversación"""
        conversacion = self.get_object()
        messages = conversacion.messages.all().order_by('created_at')
        
        # Paginación opcional
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Enviar un mensaje en una conversación"""
        conversacion = self.get_object()
        
        data = request.data.copy()
        data['conversacion'] = conversacion.id
        data['direction'] = 'OUTBOUND'
        data['sender_user'] = request.user.id
        
        serializer = CreateMessageSerializer(data=data)
        if serializer.is_valid():
            message = serializer.save()
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marcar todos los mensajes entrantes como leídos"""
        conversacion = self.get_object()
        
        updated = conversacion.messages.filter(
            direction='INBOUND',
            read_at__isnull=True
        ).update(read_at=timezone.now())
        
        return Response({
            'status': 'success',
            'messages_marked': updated
        })
    
    @action(detail=True, methods=['patch'])
    def close(self, request, pk=None):
        """Cerrar una conversación"""
        conversacion = self.get_object()
        conversacion.status = 'CLOSED'
        conversacion.save()
        
        serializer = self.get_serializer(conversacion)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_sender(self, request):
        """Obtener conversación por sender_id"""
        sender_id = request.query_params.get('sender_id')
        
        if not sender_id:
            return Response(
                {'error': 'sender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        team = self.get_user_team()
        
        if not team:
            return Response(
                {'error': 'Usuario no pertenece a ningún team'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversacion = get_object_or_404(
            Conversacion,
            sender_id=sender_id,
            team=team
        )
        
        serializer = ConversacionDetailSerializer(conversacion)
        return Response(serializer.data)

class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar mensajes"""
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    
    def get_user_team(self):
        """Obtiene el team del usuario autenticado"""
        try:
            team_member = TeamMember.objects.filter(user=self.request.user).first()
            if team_member:
                return team_member.team
            return None
        except TeamMember.DoesNotExist:
            return None
    
    def get_queryset(self):
        team = self.get_user_team()
        
        if not team:
            return Message.objects.none()
        
        return Message.objects.filter(
            conversacion__team=team
        ).select_related('conversacion', 'sender_user')
    
    def create(self, request, *args, **kwargs):
        """Crear un nuevo mensaje"""
        serializer = CreateMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)