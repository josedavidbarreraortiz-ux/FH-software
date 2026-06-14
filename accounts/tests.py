import bcrypt
from datetime import datetime
from django.test import TestCase
from django.urls import reverse
from django.core import mail
from accounts.models import User
from accounts.backends import FHAuthBackend
from accounts.views import _generate_token, _hash_token

# Helper function to create users in tests
def create_test_user(email="test@example.com", name="Test User", password="password123", role="USER", enabled=True):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return User.objects.create(
        name=name,
        email=email,
        password=hashed,
        enabled=enabled,
        role=role,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


class AccountsUnitTests(TestCase):
    """Pruebas unitarias para modelos y backend de autenticación de accounts."""

    def test_user_model_properties(self):
        user_admin = create_test_user(email="admin@example.com", name="Admin User", role="ADMIN")
        user_vendedor = create_test_user(email="vendor@example.com", name="Vendor User", role="VENDEDOR")
        user_regular = create_test_user(email="user@example.com", name="Regular User", role="USER")

        assert str(user_regular) == "Regular User"
        assert user_admin.is_admin is True
        assert user_admin.is_vendedor is False
        assert user_vendedor.is_admin is False
        assert user_vendedor.is_vendedor is True
        assert user_regular.is_admin is False
        assert user_regular.is_vendedor is False

    def test_user_save_enabled_bytes(self):
        user = User(
            name="Byte Test",
            email="byte@example.com",
            password="password123",
            enabled=b'\x01',  # Simula valor binario (BIT) desde BD
            role="USER"
        )
        user.save()
        assert user.enabled is True

        user2 = User(
            name="Byte Test False",
            email="byte_false@example.com",
            password="password123",
            enabled=b'\x00',
            role="USER"
        )
        user2.save()
        assert user2.enabled is False

    def test_password_recovery_helpers(self):
        token = _generate_token()
        assert len(token) == 64
        hashed = _hash_token(token)
        assert len(hashed) == 64
        assert hashed == _hash_token(token)
        assert hashed != token

    def test_fh_auth_backend(self):
        create_test_user(email="auth@example.com", password="secure_password_123")
        backend = FHAuthBackend()

        user = backend.authenticate(None, email="auth@example.com", password="secure_password_123")
        assert user is not None
        assert user.email == "auth@example.com"

        user_wrong = backend.authenticate(None, email="auth@example.com", password="wrongpassword")
        assert user_wrong is None


class AccountsIntegrationTests(TestCase):
    """Pruebas de integración para las vistas y flujos de cuentas."""

    def test_login_view_get(self):
        response = self.client.get(reverse('accounts:login'))
        assert response.status_code == 200
        assert "accounts/login.html" in [t.name for t in response.templates]

    def test_login_view_post_success(self):
        # Admin redirige a /panel/
        create_test_user(email="admin@example.com", password="password123", role="ADMIN")
        response = self.client.post(reverse('accounts:login'), {
            'email': 'admin@example.com',
            'password': 'password123'
        })
        assert response.status_code == 302
        assert response.url == '/panel/'
        assert self.client.session['user_role'] == 'ADMIN'

        # Usuario normal redirige a /
        self.client.session.flush()
        create_test_user(email="user@example.com", password="password123", role="USER")
        response2 = self.client.post(reverse('accounts:login'), {
            'email': 'user@example.com',
            'password': 'password123'
        })
        assert response2.status_code == 302
        assert response2.url == '/'
        assert self.client.session['user_role'] == 'USER'

    def test_login_view_post_failure(self):
        create_test_user(email="user@example.com", password="password123")
        response = self.client.post(reverse('accounts:login'), {
            'email': 'user@example.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 200
        messages = list(response.context['messages'])
        assert len(messages) > 0
        assert str(messages[0]) == "Correo o contraseña incorrectos."

    def test_register_view_success(self):
        response = self.client.post(reverse('accounts:register'), {
            'name': 'New Client',
            'email': 'newclient@example.com',
            'password': 'password123',
            'password2': 'password123'
        })
        assert response.status_code == 302
        assert response.url == reverse('accounts:login')
        
        user = User.objects.get(email='newclient@example.com')
        assert user.name == 'New Client'
        assert user.role == 'USER'

    def test_register_view_validation_errors(self):
        # Las contraseñas no coinciden
        response = self.client.post(reverse('accounts:register'), {
            'name': 'New Client',
            'email': 'newclient@example.com',
            'password': 'password123',
            'password2': 'different_pass'
        })
        assert response.status_code == 200
        messages = [str(m) for m in list(response.context['messages'])]
        assert "Las contraseñas no coinciden." in messages

        # Correo duplicado
        create_test_user(email="existing@example.com")
        response2 = self.client.post(reverse('accounts:register'), {
            'name': 'Another Name',
            'email': 'existing@example.com',
            'password': 'password123',
            'password2': 'password123'
        })
        assert response2.status_code == 200
        messages2 = [str(m) for m in list(response2.context['messages'])]
        assert "Este correo ya está registrado." in messages2

    def test_logout_view(self):
        user = create_test_user(email="logout@example.com")
        session = self.client.session
        session['user_id'] = user.id
        session['user_name'] = user.name
        session.save()

        response = self.client.get(reverse('accounts:logout'))
        assert response.status_code == 302
        assert response.url == reverse('accounts:login')
        assert 'user_id' not in self.client.session

    def test_password_recovery_integration(self):
        user = create_test_user(email="recover@example.com", password="oldpassword")
        
        # 1. Enviar solicitud de recuperación
        response = self.client.post(reverse('accounts:password_reset'), {
            'email': 'recover@example.com'
        })
        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert "Recupera tu contraseña" in mail.outbox[0].subject
        
        user.refresh_from_db()
        assert user.remember_token is not None
        
        # Obtener el token del correo enviado
        reset_mail_body = mail.outbox[0].body
        import re
        match = re.search(r'/accounts/password-reset/confirm/\d+/([a-f0-9]+)/', reset_mail_body)
        assert match is not None
        raw_token = match.group(1)

        # 2. Confirmar nueva contraseña con el token
        confirm_url = reverse('accounts:password_reset_confirm', args=[user.id, raw_token])
        response_get = self.client.get(confirm_url)
        assert response_get.status_code == 200
        
        # 3. Guardar nueva contraseña
        response_post = self.client.post(confirm_url, {
            'password': 'newpassword123',
            'password2': 'newpassword123'
        })
        assert response_post.status_code == 302
        assert response_post.url == reverse('accounts:login')
        
        # Verificar restablecimiento
        user.refresh_from_db()
        assert user.remember_token is None
        
        # Probar autenticación con nueva contraseña
        backend = FHAuthBackend()
        assert backend.authenticate(None, email="recover@example.com", password="newpassword123") is not None
