# apps/usuarios/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Adapter personalizado para que los correos de verificación
    apunten al frontend (SPA) en lugar de al backend.
    """

    def get_email_confirmation_url(self, request, emailconfirmation):
        """
        Construye la URL de confirmación de email apuntando al frontend.
        Usa FRONTEND_URL de settings para soportar dev vs producción.
        """
        return f"{settings.FRONTEND_URL}/verify-email/{emailconfirmation.key}"
