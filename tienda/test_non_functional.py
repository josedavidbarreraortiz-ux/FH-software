import time
from django.test import TestCase
from django.urls import reverse
from accounts.models import Producto, Categoria

class TiendaNonFunctionalTests(TestCase):
    """Pruebas No Funcionales para la aplicación tienda (Eficiencia BD y Carga)."""

    def setUp(self):
        # Crear datos iniciales necesarios para las pruebas
        self.categoria = Categoria.objects.create(
            categoria_nombre="Tecnología",
            descripcion="Artículos tecnológicos",
            estado=1
        )

    # ── Rendimiento ─────────────────────────────────────────────────────────

    def test_catalogo_page_performance(self):
        """Rendimiento: La página del catálogo debe responder en menos de 200ms."""
        # Registrar un producto para poblar la vista
        Producto.objects.create(
            producto_nombre="Producto Rendimiento",
            producto_precio_venta=100000,
            producto_estado="Activo",
            categoria=self.categoria
        )
        
        start_time = time.time()
        response = self.client.get(reverse('tienda:catalogo'))
        duration = (time.time() - start_time) * 1000  # Convertir a milisegundos

        assert response.status_code == 200
        assert duration < 200, f"El catálogo tardó demasiado en responder: {duration:.2f}ms (límite 200ms)"

    # ── Eficiencia de Base de Datos (N+1 Query Detection) ───────────────────

    def test_catalogo_n_plus_one_prevention(self):
        """Eficiencia de BD: Verificar que las consultas a la base de datos sean constantes O(1) y no O(N)."""
        # 1. Crear 1 producto inicial y medir cantidad de queries de base de datos
        Producto.objects.create(
            producto_nombre="Prod 1",
            producto_precio_venta=50000,
            producto_estado="Activo",
            categoria=self.categoria
        )
        
        from django.db import connection
        connection.queries_log.clear()
        
        self.client.get(reverse('tienda:catalogo'))
        queries_with_one_product = len(connection.queries)

        # 2. Agregar 10 productos adicionales
        for i in range(2, 12):
            Producto.objects.create(
                producto_nombre=f"Prod {i}",
                producto_precio_venta=50000,
                producto_estado="Activo",
                categoria=self.categoria
            )

        connection.queries_log.clear()
        
        # 3. Medir consultas con 11 productos
        self.client.get(reverse('tienda:catalogo'))
        queries_with_eleven_products = len(connection.queries)

        # 4. Asegurar que la cantidad de consultas de base de datos no aumentó
        # (Si aumentó, significa que se hacen consultas adicionales por cada producto individual)
        assert queries_with_one_product == queries_with_eleven_products, (
            f"Se detectó un problema de consultas N+1 en el catálogo. "
            f"Queries con 1 prod: {queries_with_one_product} vs con 11 prod: {queries_with_eleven_products}"
        )

    # ── Carga / Estrés ligero ───────────────────────────────────────────────

    def test_home_sequential_load_stability(self):
        """Rendimiento: Simular 20 peticiones consecutivas y verificar estabilidad en el tiempo de respuesta."""
        num_requests = 20
        total_duration = 0.0

        for _ in range(num_requests):
            start_time = time.time()
            response = self.client.get(reverse('tienda:index'))
            assert response.status_code == 200
            total_duration += (time.time() - start_time)

        average_duration = (total_duration / num_requests) * 1000  # En milisegundos
        
        # El tiempo medio por petición bajo carga secuencial debe ser menor a 50ms en la base de datos de pruebas
        assert average_duration < 50, f"Estabilidad comprometida: tiempo medio de respuesta {average_duration:.2f}ms (límite 50ms)"
