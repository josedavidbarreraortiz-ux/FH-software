import os
import django
from django.test.utils import setup_test_environment, teardown_test_environment

# Asegurar que la variable de entorno de configuración de Django esté establecida
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fh_project.settings')

def pytest_configure(config):
    """
    Hook de pytest para inicializar Django, configurar el entorno de pruebas,
    forzar que los modelos de la base de datos sean gestionados, correr las
    migraciones del sistema y crear dinámicamente las tablas de los modelos del proyecto.
    """
    django.setup()
    
    # 1. Configurar el entorno de pruebas (habilita la captura de templates y el backend de correo locmem)
    setup_test_environment()
    
    # 2. Hacer que todos los modelos tengan managed=True para poder crear las tablas
    from django.apps import apps
    for model in apps.get_models():
        model._meta.managed = True
        
    # 3. Ejecutar las migraciones estándar de Django (sesiones, contenttypes, etc.)
    from django.core.management import call_command
    print("\n[Pytest Django Setup] Ejecutando migraciones de Django...")
    call_command('migrate', interactive=False, verbosity=0)

    # 4. Crear las tablas de nuestras aplicaciones usando el schema_editor de Django
    from django.db import connection
    print("[Pytest Django Setup] Creando tablas para los modelos del proyecto...")
    with connection.schema_editor() as schema_editor:
        for model in apps.get_models():
            # Crear tablas solo de nuestras aplicaciones personalizadas
            if model._meta.app_label in ['accounts', 'tienda', 'admin_panel']:
                try:
                    schema_editor.create_model(model)
                except Exception as e:
                    print(f"Advertencia al crear tabla para {model.__name__}: {e}")


def pytest_unconfigure(config):
    """
    Hook de pytest para limpiar el entorno de pruebas y eliminar el archivo
    de base de datos temporal al finalizar la ejecución de todas las pruebas.
    """
    # Desmantelar el entorno de pruebas
    teardown_test_environment()

    db_path = 'test_db.sqlite3'
    if os.path.exists(db_path):
        try:
            # Cerrar conexiones activas para evitar bloqueos del archivo en Windows
            from django.db import connections
            for conn in connections.all():
                conn.close()
            
            os.remove(db_path)
            print("\n[Pytest Django Teardown] Base de datos de pruebas eliminada correctamente.")
        except Exception as e:
            print(f"\n[Pytest Django Teardown] No se pudo eliminar la base de datos de pruebas: {e}")
