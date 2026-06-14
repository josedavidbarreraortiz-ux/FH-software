import bcrypt
from datetime import datetime, date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import (
    Producto, Categoria, Inventario, Venta, VentaDetalle,
    MetodoPago, MovimientoInventario, User
)

# Helper functions to set up entities for tienda tests
def create_test_user(email="buyer@example.com", name="Buyer Name"):
    hashed = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return User.objects.create(
        name=name,
        email=email,
        password=hashed,
        enabled=True,
        role="USER",
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

def create_test_category(nombre="Tecnología"):
    return Categoria.objects.create(
        categoria_nombre=nombre,
        descripcion="Descripción de categoría",
        estado=1
    )

def create_test_product(nombre="Mouse Inalámbrico", precio=50000.0, categoria=None, estado="Activo", create_cat_if_none=True):
    if categoria is None and create_cat_if_none:
        categoria = create_test_category()
    return Producto.objects.create(
        producto_nombre=nombre,
        producto_precio_venta=precio,
        producto_estado=estado,
        categoria=categoria,
        producto_codigo_bar="987654321",
        tipo_unidad="Unidad",
        producto_marca="Logitech",
        especificacion="Especificación",
        resumen="Resumen"
    )


class TiendaUnitTests(TestCase):
    """Pruebas unitarias para modelos y lógica de la tienda."""

    def test_producto_precio_formateado(self):
        p1 = create_test_product(precio=Decimal('150000.50'))
        assert p1.precio_formateado == "$150,000"  # El redondeo bancario de Python redondea a par más cercano (150000)
        
        p2 = create_test_product(precio=None)
        assert p2.precio_formateado == "$0"

    def test_producto_get_categoria_nombre(self):
        cat = create_test_category(nombre="Audio")
        p1 = create_test_product(categoria=cat)
        assert p1.get_categoria_nombre == "Audio"
        
        p2 = create_test_product(categoria=None, create_cat_if_none=False)
        assert p2.get_categoria_nombre == "Sin categoría"

    def test_inventario_stock_bajo(self):
        p = create_test_product()
        
        # Caso 1: Stock actual es menor o igual al mínimo
        inv1 = Inventario(
            producto=p,
            inventario_stock_actual=5,
            inventario_stock_minimo=10,
            inventario_stock_maximo=50
        )
        assert inv1.stock_bajo is True

        # Caso 2: Stock actual es mayor al mínimo
        inv2 = Inventario(
            producto=p,
            inventario_stock_actual=15,
            inventario_stock_minimo=10,
            inventario_stock_maximo=50
        )
        assert inv2.stock_bajo is False


class TiendaIntegrationTests(TestCase):
    """Pruebas de integración para las vistas y flujos del catálogo y compras."""

    def test_catalogo_view_filters(self):
        cat_tecnologia = create_test_category(nombre="Tecnología")
        cat_hogar = create_test_category(nombre="Hogar")
        
        create_test_product(nombre="Mouse Gamer", precio=45000.0, categoria=cat_tecnologia)
        create_test_product(nombre="Teclado Mecánico", precio=120000.0, categoria=cat_tecnologia)
        create_test_product(nombre="Licuadora", precio=80000.0, categoria=cat_hogar)

        # 1. Cargar catálogo sin filtros
        response = self.client.get(reverse('tienda:catalogo'))
        assert response.status_code == 200
        assert len(response.context['productos']) == 3

        # 2. Filtrar por búsqueda de texto
        response_q = self.client.get(f"{reverse('tienda:catalogo')}?q=Teclado")
        assert response_q.status_code == 200
        assert len(response_q.context['productos']) == 1
        assert response_q.context['productos'][0].producto_nombre == "Teclado Mecánico"

        # 3. Filtrar por precio máximo
        response_price = self.client.get(f"{reverse('tienda:catalogo')}?precio_max=90000")
        assert response_price.status_code == 200
        prod_names = [p.producto_nombre for p in response_price.context['productos']]
        assert "Mouse Gamer" in prod_names
        assert "Licuadora" in prod_names
        assert "Teclado Mecánico" not in prod_names

        # 4. Filtrar por categoría
        response_cat = self.client.get(f"{reverse('tienda:catalogo')}?categoria={cat_hogar.categoria_id}")
        assert response_cat.status_code == 200
        assert len(response_cat.context['productos']) == 1
        assert response_cat.context['productos'][0].producto_nombre == "Licuadora"

    def test_carrito_gestion(self):
        user = create_test_user()
        p = create_test_product(nombre="Auriculares", precio=90000.0)
        
        Inventario.objects.create(
            producto=p,
            inventario_stock_actual=10,
            inventario_stock_minimo=2,
            inventario_stock_maximo=20
        )

        # Autenticar al usuario simulando variables de sesión
        session = self.client.session
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        session.save()

        # 1. Agregar al carrito
        url_agregar = reverse('tienda:carrito_agregar', args=[p.producto_id])
        response_add = self.client.post(url_agregar, {'cantidad': 2}, HTTP_REFERER=reverse('tienda:catalogo'))
        assert response_add.status_code == 302
        assert self.client.session['carrito'] == {str(p.producto_id): 2}

        # 2. Ver la página del carrito
        response_cart = self.client.get(reverse('tienda:carrito'))
        assert response_cart.status_code == 200
        assert response_cart.context['total'] == Decimal('180000.00')

        # 3. Actualizar la cantidad
        url_actualizar = reverse('tienda:carrito_actualizar', args=[p.producto_id])
        response_update = self.client.post(url_actualizar, {'cantidad': 5})
        assert response_update.status_code == 302
        assert self.client.session['carrito'] == {str(p.producto_id): 5}

        # 4. Eliminar del carrito
        url_eliminar = reverse('tienda:carrito_eliminar', args=[p.producto_id])
        response_delete = self.client.get(url_eliminar)
        assert response_delete.status_code == 302
        assert self.client.session['carrito'] == {}

    def test_checkout_proceso_compra(self):
        user = create_test_user()
        p = create_test_product(nombre="Silla Oficina", precio=250000.0)
        
        Inventario.objects.create(
            producto=p,
            inventario_stock_actual=15,
            inventario_stock_minimo=2,
            inventario_stock_maximo=30
        )

        metodo_pago = MetodoPago.objects.create(
            metodo_pago_id=1,
            metodo_pago_nombre="Transferencia Bancaria"
        )

        session = self.client.session
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        session['carrito'] = {str(p.producto_id): 2}
        session.save()

        # Checkout GET
        response_get = self.client.get(reverse('tienda:checkout'))
        assert response_get.status_code == 200

        # Checkout POST (Compra)
        response_post = self.client.post(reverse('tienda:checkout'), {
            'nombre': user.name,
            'email': user.email,
            'telefono': '3001234567',
            'documento': '10203040',
            'direccion': 'Calle Falsa 123',
            'metodo_pago': metodo_pago.metodo_pago_id,
            'observaciones': 'Entregar por la tarde'
        })
        assert response_post.status_code == 302
        assert response_post.url == reverse('tienda:pedidos')

        # Validar base de datos
        venta = Venta.objects.get(comprador_id=user.id)
        assert venta.venta_total == Decimal('500000.00')

        detalle = VentaDetalle.objects.get(venta=venta)
        assert detalle.producto == p
        assert detalle.venta_detalle_cantidad == 2

        movimiento = MovimientoInventario.objects.get(producto=p)
        assert movimiento.movimiento_tipo == 'SALIDA'
        assert movimiento.movimiento_cantidad == 2

        # Carrito debe limpiarse
        assert self.client.session['carrito'] == {}

        # Perfil del usuario actualizado
        user.refresh_from_db()
        assert user.telefono == '3001234567'
        assert user.direccion == 'Calle Falsa 123'
