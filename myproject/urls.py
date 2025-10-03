
# myproject/urls.py (URL principal)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from apps.usuarios.views import CustomTokenObtainPairView
from apps.flows.views import FlowWebhookView

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response("OK")

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    path('api/', include('apps.usuarios.urls')),
    path('api/', include('apps.teams.urls')), 
    path('api/', include('apps.tasks.urls')),
    path('api/', include('apps.integraciones.urls')),
    path('api/', include('apps.flows.urls')),
    #path('api/', include('apps.mensajes.urls')),
    #path('api/', include('apps.conversaciones.urls')),
    #path('api/', include('apps.leads.urls')),


    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('webhook/<slug:team_slug>/<slug:flow_slug>/', FlowWebhookView.as_view(), name='flow-webhook'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
