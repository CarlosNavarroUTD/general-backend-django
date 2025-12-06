from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    """
    Permite autenticación usando el campo 'email' en lugar de 'username'.
    """
    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        print(f"🔧 EmailBackend llamado con email={email}, username={username}")
        
        # Permitir usar 'username' o 'email' como parámetro
        if email is None:
            email = username
            
        if email is None or password is None:
            print("❌ Email o password es None")
            return None
            
        try:
            user = UserModel.objects.get(email=email)
            print(f"✅ Usuario encontrado: {user.email}")
        except UserModel.DoesNotExist:
            print(f"❌ Usuario no existe con email: {email}")
            return None
        except UserModel.MultipleObjectsReturned:
            print(f"⚠️ Múltiples usuarios con email: {email}")
            return None

        if user.check_password(password):
            print(f"✅ Password correcto para: {user.email}")
            if self.user_can_authenticate(user):
                print(f"✅ Usuario puede autenticarse")
                return user
            else:
                print(f"❌ Usuario no puede autenticarse (is_active={user.is_active})")
        else:
            print(f"❌ Password incorrecto")
            
        return None