from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from accounts.models import User
from accounts.backends import FHAuthBackend
import bcrypt
import hashlib
import secrets
from datetime import datetime


def login_view(request):
    if request.session.get('user_id'):
        return redirect('/')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        backend = FHAuthBackend()
        user = backend.authenticate(request, email=email, password=password)
        
        if user:
            request.session['user_id'] = user.id
            request.session['user_name'] = user.name
            request.session['user_email'] = user.email
            request.session['user_role'] = user.role
            
            if user.role in ('ADMIN', 'VENDEDOR'):
                return redirect('/panel/')
            else:
                return redirect('/')
        else:
            messages.error(request, 'Correo o contraseña incorrectos.')
    
    return render(request, 'accounts/login.html')


def register_view(request):
    if request.session.get('user_id'):
        return redirect('/')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')
        
        errors = []
        if not name:
            errors.append('El nombre es obligatorio.')
        if not email:
            errors.append('El correo es obligatorio.')
        if not password or len(password) < 6:
            errors.append('La contraseña debe tener al menos 6 caracteres.')
        if password != password2:
            errors.append('Las contraseñas no coinciden.')
        if User.objects.filter(email=email).exists():
            errors.append('Este correo ya está registrado.')
        
        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/register.html', {
                'name': name, 'email': email,
            })
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        User.objects.create(
            name=name,
            email=email,
            password=hashed,
            enabled=True,
            role='USER',
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        messages.success(request, '¡Registro exitoso! Ahora puedes iniciar sesión.')
        return redirect('/accounts/login/')
    
    return render(request, 'accounts/register.html')


def logout_view(request):
    request.session.flush()
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('/accounts/login/')


# ── Password Recovery ──────────────────────────────────────────────

def _generate_token():
    """Genera un token seguro de 64 caracteres hexadecimales."""
    return secrets.token_hex(32)


def _hash_token(token):
    """Crea un hash SHA-256 del token para almacenar en la BD."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def password_reset_request_view(request):
    """Paso 1: El usuario ingresa su correo y se le envía un enlace de recuperación."""
    if request.session.get('user_id'):
        return redirect('/')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        # Siempre mostramos el mismo mensaje para no revelar si el email existe
        success_msg = (
            'Si el correo está registrado, recibirás un enlace para '
            'restablecer tu contraseña en los próximos minutos.'
        )

        if email:
            try:
                user = User.objects.get(email=email, enabled=True)

                # Generar token y guardar su hash en remember_token
                raw_token = _generate_token()
                # Formato: timestamp|hash  → permite verificar expiración
                token_data = f"{int(datetime.now().timestamp())}|{_hash_token(raw_token)}"
                user.remember_token = token_data
                user.updated_at = datetime.now()
                user.save(update_fields=['remember_token', 'updated_at'])

                # Construir enlace de recuperación
                protocol = 'https' if request.is_secure() else 'http'
                host = request.get_host()
                reset_url = f"{protocol}://{host}/accounts/password-reset/confirm/{user.id}/{raw_token}/"

                # Enviar correo
                _send_reset_email(user, reset_url)

            except User.DoesNotExist:
                pass  # No revelamos que el correo no existe
            except Exception:
                pass  # Fallo silencioso para no revelar información

        messages.success(request, success_msg)
        return render(request, 'accounts/password_reset_request.html', {'email_sent': True})

    return render(request, 'accounts/password_reset_request.html')


def _send_reset_email(user, reset_url):
    """Envía el correo de recuperación de contraseña."""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    subject = 'Recupera tu contraseña — FH TechStore'

    html_message = render_to_string('accounts/email_password_reset.html', {
        'user': user,
        'reset_url': reset_url,
        'expire_hours': getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600) // 3600,
    })

    plain_message = strip_tags(html_message)

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )


def password_reset_confirm_view(request, user_id, token):
    """Paso 2: El usuario abre el enlace y establece su nueva contraseña."""

    # Validar token
    try:
        user = User.objects.get(id=user_id, enabled=True)
    except User.DoesNotExist:
        messages.error(request, 'El enlace de recuperación no es válido.')
        return redirect('/accounts/password-reset/')

    if not user.remember_token:
        messages.error(request, 'El enlace de recuperación ya fue utilizado o expiró.')
        return redirect('/accounts/password-reset/')

    # Parsear token almacenado: "timestamp|hash"
    try:
        parts = user.remember_token.split('|')
        stored_timestamp = int(parts[0])
        stored_hash = parts[1]
    except (ValueError, IndexError):
        messages.error(request, 'El enlace de recuperación no es válido.')
        return redirect('/accounts/password-reset/')

    # Verificar expiración
    timeout = getattr(settings, 'PASSWORD_RESET_TIMEOUT', 3600)
    elapsed = int(datetime.now().timestamp()) - stored_timestamp
    if elapsed > timeout:
        # Limpiar token expirado
        user.remember_token = None
        user.save(update_fields=['remember_token'])
        messages.error(request, 'El enlace de recuperación ha expirado. Solicita uno nuevo.')
        return redirect('/accounts/password-reset/')

    # Verificar hash del token
    if _hash_token(token) != stored_hash:
        messages.error(request, 'El enlace de recuperación no es válido.')
        return redirect('/accounts/password-reset/')

    # Si llega aquí, el token es válido
    if request.method == 'POST':
        password = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        errors = []
        if not password or len(password) < 6:
            errors.append('La contraseña debe tener al menos 6 caracteres.')
        if password != password2:
            errors.append('Las contraseñas no coinciden.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'accounts/password_reset_confirm.html', {
                'user_id': user_id,
                'token': token,
            })

        # Actualizar contraseña
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user.password = hashed
        user.remember_token = None  # Invalidar token después de usarlo
        user.updated_at = datetime.now()
        user.save(update_fields=['password', 'remember_token', 'updated_at'])

        messages.success(request, '¡Tu contraseña ha sido restablecida exitosamente! Ya puedes iniciar sesión.')
        return redirect('/accounts/login/')

    return render(request, 'accounts/password_reset_confirm.html', {
        'user_id': user_id,
        'token': token,
    })
