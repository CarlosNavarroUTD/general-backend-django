# apps/integraciones/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.teams.models import TeamMember, Team
from .models import GoogleMapsIntegration, GooglePlaceBusiness

from rest_framework.viewsets import ModelViewSet
from .serializers import GooglePlaceBusinessSerializer

from .services.google_maps import obtener_comentarios_google

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

from rest_framework.permissions import IsAuthenticated
from .models import GoogleToken



class GooglePlaceBusinessViewSet(ModelViewSet):
    serializer_class = GooglePlaceBusinessSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        team_id = self.request.query_params.get('team_id')
        
        if team_id:
            # Verificar que el usuario pertenezca al equipo
            try:
                team = Team.objects.get(id=team_id)
                if TeamMember.objects.filter(user=user, team=team).exists():
                    return GooglePlaceBusiness.objects.filter(team=team)
            except Team.DoesNotExist:
                pass
        
        return GooglePlaceBusiness.objects.none()

class GoogleBusinessCommentsView(APIView):
    def get(self, request):
        user = request.user
        business_id = request.query_params.get("business_id")
        team_id = request.query_params.get("team_id")
        
        if not all([business_id, team_id]):
            return Response({"error": "Faltan parámetros requeridos"}, status=400)
        
        try:
            # Verificar permisos
            team = Team.objects.get(id=team_id)
            if not TeamMember.objects.filter(user=user, team=team).exists():
                return Response({"error": "Sin permisos"}, status=403)
            
            # Obtener negocio
            business = GooglePlaceBusiness.objects.get(id=business_id, team=team)
            
            # Obtener token
            token_obj = GoogleToken.objects.get(user=user)
            if token_obj.is_expired():
                return Response({"error": "Token expirado"}, status=401)
            
            # Obtener comentarios
            comentarios = obtener_comentarios_google(business.place_id, token_obj.access_token)
            
            return Response({
                "business_id": business.id,
                "business_name": business.name,
                "place_id": business.place_id,
                "comentarios": comentarios.get('result', {}).get('reviews', []),
                "total_reviews": len(comentarios.get('result', {}).get('reviews', [])),
                "average_rating": business.rating
            }, status=200)
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GoogleAuthStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            token_obj = GoogleToken.objects.get(user=user)
            return Response({
                "authenticated": True,
                "expires_at": token_obj.expires_at,
                "is_expired": token_obj.is_expired()
            })
        except GoogleToken.DoesNotExist:
            return Response({"authenticated": False}, status=200)

# ========== VISTAS PARA COMENTARIOS GOOGLE  ==========

class GoogleComentariosView(APIView):
    def get(self, request):
        user = request.user
        team_id = request.query_params.get("team_id")

        if not team_id:
            return Response({"error": "Falta el parámetro team_id"}, status=400)

        # Verificar que el usuario pertenezca al equipo
        try:
            team = Team.objects.get(id=team_id)
            if not TeamMember.objects.filter(user=user, team=team).exists():
                return Response({"error": "No tienes acceso a este equipo"}, status=403)
        except Team.DoesNotExist:
            return Response({"error": "El equipo no existe"}, status=404)

        # Buscar integración activa
        try:
            token_obj = GoogleToken.objects.get(user=user)
            if token_obj.is_expired():
                # Aquí puedes implementar la lógica para refrescar el token si tienes el refresh_token
                return Response({"error": "El token de Google ha expirado"}, status=401)
            
            integracion = GoogleMapsIntegration.objects.get(team=team, activo=True)
            comentarios = obtener_comentarios_google(integracion.place_id, token_obj.access_token)

            return Response({"comentarios": comentarios}, status=200)
        except GoogleMapsIntegration.DoesNotExist:
            return Response({"error": "El equipo no tiene integración activa de Google Maps"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# ========== VISTAS PARA GOOGLE OAUTH ==========

@api_view(['GET'])
@permission_classes([AllowAny])
def google_auth_redirect(request):
    """
    Endpoint que redirige a Google OAuth
    """
    try:
        # Obtener configuración de Google OAuth
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        
        if not client_id:
            return JsonResponse({'error': 'Google OAuth no configurado'}, status=500)
        
        # Construir URL de autorización de Google
        google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        
        # IMPORTANTE: Esta URL debe coincidir exactamente con la registrada en Google Console
        redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'https://http://127.0.0.1:8000/api/auth/google/callback/')
        

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': 'openid email profile',
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }

        
        auth_url = f"{google_auth_url}?{urllib.parse.urlencode(params)}"
        
        print(f"Redirigiendo a Google OAuth: {auth_url}")
        print(f"Redirect URI configurada: {redirect_uri}")
        
        return redirect(auth_url)
        
    except Exception as e:
        print(f"Error en google_auth_redirect: {str(e)}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class GoogleAuthCallbackView(View):
    """
    Vista que maneja el callback de Google OAuth y redirige al frontend con los datos
    """
    def get(self, request):
        print("=== INICIO CALLBACK DE GOOGLE ===")
        print(f"Query params: {request.GET}")
        
        # Verificar si hay error en la respuesta de Google
        error = request.GET.get('error')
        if error:
            print(f"Error de Google: {error}")
            frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback?error=google_auth_error"
            return redirect(frontend_url)
        
        # Obtener el código de autorización
        code = request.GET.get('code')
        if not code:
            print("No se recibió código de autorización")
            frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback?error=no_code"
            return redirect(frontend_url)
        
        print(f"Código recibido: {code[:20]}...")
        
        try:
            # Intercambiar código por tokens con Google
            print("Intercambiando código por tokens...")
            token_data = self._exchange_code_for_tokens(code, request)
            print("Tokens obtenidos exitosamente")
            
            # Obtener información del usuario de Google
            print("Obteniendo información del usuario...")
            user_info = self._get_user_info_from_google(token_data['access_token'])
            print(f"Usuario obtenido: {user_info.get('email')}")
            
            # Crear o obtener usuario en Django
            print("Creando/obteniendo usuario en Django...")
            user = self._get_or_create_user(user_info)
            print(f"Usuario Django: {user.email}")
            
            from apps.integraciones.models import GoogleToken
            from django.utils.timezone import now, timedelta

            GoogleToken.objects.update_or_create(
                user=user,
                defaults={
                    'access_token': token_data['access_token'],
                    'refresh_token': token_data.get('refresh_token', ''),  # puede venir vacío si no es la 1ra vez
                    'expires_at': now() + timedelta(seconds=int(token_data['expires_in']))
                }
            )

            # Generar tokens JWT
            print("Generando tokens JWT...")
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Preparar datos del usuario
            user_data = {
                'id': user.id_usuario,
                'email': user.email,
                'nombre_usuario': user.nombre_usuario,
                'tipo_usuario': user.tipo_usuario
            }
            
            print("=== ÉXITO - Redirigiendo al frontend con tokens ===")
            
            # Redirigir al frontend con los datos como parámetros de URL
            frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback"
            params = {
                'success': 'true',
                'access': access_token,
                'refresh': refresh_token,
                'user': json.dumps(user_data)
            }
            
            redirect_url = f"{frontend_url}?{urllib.parse.urlencode(params)}"
            return redirect(redirect_url)
            
        except Exception as e:
            print(f"Error en Google OAuth: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Redirigir al frontend con error
            frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback?error=auth_failed&message={urllib.parse.quote(str(e))}"
            return redirect(frontend_url)
    
    def _exchange_code_for_tokens(self, code, request):
        """Intercambia el código de autorización por tokens de acceso"""
        token_url = "https://oauth2.googleapis.com/token"
        redirect_uri = getattr(settings, 'GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/auth/google/callback/')
        
        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        print(f"Enviando request a Google token endpoint con redirect_uri: {redirect_uri}")
        
        response = requests.post(token_url, data=data)
        
        if not response.ok:
            print(f"Error en token exchange: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def _get_user_info_from_google(self, access_token):
        """Obtiene información del usuario desde Google"""
        user_info_url = f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}"
        response = requests.get(user_info_url)
        
        if not response.ok:
            print(f"Error obteniendo user info: {response.status_code} - {response.text}")
            response.raise_for_status()
        
        return response.json()
    
    def _get_or_create_user(self, user_info):
        """Crea o obtiene un usuario basado en la información de Google"""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        email = user_info.get('email')
        
        if not email:
            raise ValueError("Email no proporcionado por Google")
        
        # Buscar usuario existente
        try:
            user = User.objects.get(email=email)
            print(f"Usuario existente encontrado: {user.email}")
            return user
        except User.DoesNotExist:
            # Crear nuevo usuario - solo con campos que existen en tu modelo
            print(f"Creando nuevo usuario para: {email}")
            
            # Crear nombre_usuario a partir del email
            nombre_usuario = email.split('@')[0]
            
            # Asegurar que el nombre_usuario sea único
            counter = 1
            original_nombre = nombre_usuario
            while User.objects.filter(nombre_usuario=nombre_usuario).exists():
                nombre_usuario = f"{original_nombre}_{counter}"
                counter += 1
            
            user = User.objects.create_user(
                email=email,
                nombre_usuario=nombre_usuario,
                tipo_usuario='usuario'  # Valor por defecto
            )
            
            # Crear el registro en Persona si es necesario
            from apps.usuarios.models import Persona
            persona, created = Persona.objects.get_or_create(
                usuario=user,
                defaults={
                    'nombre': user_info.get('given_name', ''),
                    'apellido': user_info.get('family_name', '')
                }
            )
            if created:
                print(f"Persona creada para {user.email}")
            else:
                print(f"Persona ya existía para {user.email}")
            
            return user
    
    def refrescar_token(token_obj):
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'refresh_token': token_obj.refresh_token,
            'grant_type': 'refresh_token',
        }
        response = requests.post(token_url, data=data)
        if response.ok:
            new_data = response.json()
            token_obj.access_token = new_data['access_token']
            token_obj.expires_at = now() + timedelta(seconds=new_data['expires_in'])
            token_obj.save()
            return token_obj
        else:
            raise Exception("Error al refrescar token: " + response.text)
