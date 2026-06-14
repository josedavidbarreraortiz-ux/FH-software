import os
from django.test.runner import DiscoverRunner

class ManagedModelTestRunner(DiscoverRunner):
    """
    Test runner personalizado para Django que permite que 'manage.py test'
    cree dinámicamente las tablas de los modelos no gestionados (managed=False)
    en la base de datos de prueba SQLite.
    """

    def setup_test_environment(self, *args, **kwargs):
        # Forzar managed=True en todos los modelos
        from django.apps import apps
        for model in apps.get_models():
            model._meta.managed = True
        super().setup_test_environment(*args, **kwargs)

    def setup_databases(self, *args, **kwargs):
        # Crear la base de datos de prueba SQLite
        db_config = super().setup_databases(*args, **kwargs)
        
        # Crear las tablas para nuestras aplicaciones que no tienen migraciones
        from django.db import connection
        from django.apps import apps
        with connection.schema_editor() as schema_editor:
            for model in apps.get_models():
                if model._meta.app_label in ['accounts', 'tienda', 'admin_panel']:
                    try:
                        schema_editor.create_model(model)
                    except Exception:
                        pass
        return db_config

    def teardown_databases(self, old_config, **kwargs):
        super().teardown_databases(old_config, **kwargs)
        # Limpiar el archivo de base de datos temporal si es que persiste
        db_path = 'test_db.sqlite3'
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass
