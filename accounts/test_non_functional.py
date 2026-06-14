import time
import bcrypt
from django.test import TestCase
from django.urls import reverse

class AccountsNonFunctionalTests(TestCase):
    """Pruebas No Funcionales para la aplicación accounts (Rendimiento y Seguridad)."""

    # ── Rendimiento ─────────────────────────────────────────────────────────

    def test_login_page_response_time(self):
        """Rendimiento: La página de login debe cargar en menos de 150 milisegundos."""
        start_time = time.time()
        response = self.client.get(reverse('accounts:login'))
        duration = (time.time() - start_time) * 1000  # Convertir a milisegundos
        
        assert response.status_code == 200
        # Tolerancia de rendimiento
        assert duration < 150, f"La página de login tardó demasiado: {duration:.2f}ms (límite 150ms)"

    def test_bcrypt_work_factor_performance(self):
        """Rendimiento/Seguridad: Validar que el tiempo de hashing de contraseña esté en rango seguro."""
        password = "my_secure_password_123"
        
        start_time = time.time()
        # Generar un hash usando el factor por defecto (12 rondas)
        bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
        duration = (time.time() - start_time) * 1000  # Convertir a milisegundos

        # Rango seguro de hashing:
        # - Mayor a 50ms para prevenir ataques rápidos de fuerza bruta (Fuerza Bruta)
        # - Menor a 350ms para no saturar el CPU del servidor en picos de tráfico (DoS)
        assert 50 < duration < 350, f"El tiempo de hashing ({duration:.2f}ms) está fuera del rango seguro (50ms - 350ms)"


    # ── Seguridad ───────────────────────────────────────────────────────────

    def test_login_csrf_protection(self):
        """Seguridad: Comprobar que la vista de login requiere protección CSRF en peticiones POST."""
        from django.test import RequestFactory
        from django.middleware.csrf import CsrfViewMiddleware
        from accounts.views import login_view
        
        rf = RequestFactory()
        # Creamos una petición POST sin token CSRF
        request = rf.post(reverse('accounts:login'), {
            'email': 'hacker@badactor.com',
            'password': 'password123'
        })
        
        # Ejecutamos manualmente el middleware de CSRF
        mw = CsrfViewMiddleware(lambda req: None)
        mw.process_request(request)
        response = mw.process_view(request, login_view, (), {})
        
        # El middleware debe rechazar la petición con un error 403 Forbidden
        assert response is not None
        assert response.status_code == 403

    def test_security_headers_present(self):
        """Seguridad: Validar que las cabeceras HTTP de protección estén presentes."""
        response = self.client.get(reverse('accounts:login'))
        
        # Prevenir Clickjacking
        assert 'X-Frame-Options' in response, "Falta la cabecera X-Frame-Options para mitigar Clickjacking"
        assert response['X-Frame-Options'] in ['DENY', 'SAMEORIGIN']
