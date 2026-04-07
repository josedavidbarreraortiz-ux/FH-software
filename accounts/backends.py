import bcrypt
from accounts.models import User


class FHAuthBackend:
    """Backend de autenticación custom para verificar contraseñas bcrypt."""

    def authenticate(self, request, email=None, password=None):
        try:
            user = User.objects.get(email=email)
            if user.enabled and bcrypt.checkpw(
                password.encode('utf-8'),
                user.password.encode('utf-8')
            ):
                return user
        except User.DoesNotExist:
            return None
        except Exception:
            return None
        return None
