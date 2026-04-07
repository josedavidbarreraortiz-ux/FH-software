from django.urls import path
from accounts import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # ── Recuperación de contraseña ──
    path('password-reset/', views.password_reset_request_view, name='password_reset'),
    path('password-reset/confirm/<int:user_id>/<str:token>/', views.password_reset_confirm_view, name='password_reset_confirm'),
]
