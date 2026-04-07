from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.models import (
    Producto, Categoria, Inventario, Venta, VentaDetalle,
    Cliente, MetodoPago, MovimientoInventario, ProductoAtributo, User
)
from functools import wraps
from datetime import date, datetime
from decimal import Decimal
import json


def login_required_user(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, 'Debes iniciar sesión.')
            return redirect('/accounts/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def index(request):
    productos = Producto.objects.filter(producto_estado='Activo').select_related('categoria').order_by('producto_id')[:6]
    return render(request, 'tienda/index.html', {
        'productos': productos,
    })


def catalogo(request):
    categorias = Categoria.objects.filter(estado=1)
    categoria_id = request.GET.get('categoria')
    busqueda = request.GET.get('q', '')
    orden = request.GET.get('orden', '')
    precio_min = request.GET.get('precio_min', '')
    precio_max = request.GET.get('precio_max', '')
    
    productos = Producto.objects.filter(producto_estado='Activo').select_related('categoria')
    
    # Get max price for slider range
    from django.db.models import Max
    precio_max_total = Producto.objects.filter(producto_estado='Activo').aggregate(
        max_price=Max('producto_precio_venta')
    )['max_price'] or 10000000
    precio_max_total = int(precio_max_total)
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    if busqueda:
        productos = productos.filter(producto_nombre__icontains=busqueda)
    
    # Price range filter
    if precio_min:
        productos = productos.filter(producto_precio_venta__gte=int(precio_min))
    if precio_max:
        productos = productos.filter(producto_precio_venta__lte=int(precio_max))
    
    # Ordering
    if orden == 'precio_asc':
        productos = productos.order_by('producto_precio_venta')
    elif orden == 'precio_desc':
        productos = productos.order_by('-producto_precio_venta')
    elif orden == 'nombre_asc':
        productos = productos.order_by('producto_nombre')
    elif orden == 'nombre_desc':
        productos = productos.order_by('-producto_nombre')
    else:
        productos = productos.order_by('producto_id')
    
    return render(request, 'tienda/catalogo.html', {
        'productos': productos,
        'categorias': categorias,
        'categoria_actual': int(categoria_id) if categoria_id else None,
        'busqueda': busqueda,
        'orden': orden,
        'precio_min_val': precio_min,
        'precio_max_val': precio_max,
        'precio_max_total': precio_max_total,
    })


def producto_detalle(request, pk):
    producto = get_object_or_404(Producto.objects.select_related('categoria'), pk=pk)
    try:
        inventario = Inventario.objects.get(producto=producto)
        stock = inventario.inventario_stock_actual or 0
    except Inventario.DoesNotExist:
        stock = 0
    
    try:
        attr = ProductoAtributo.objects.select_related('valor').get(producto=producto)
        color = attr.valor.valor if attr.valor else None
    except ProductoAtributo.DoesNotExist:
        color = None
    
    cat_nombre = producto.categoria.categoria_nombre if producto.categoria else "Sin categoría"
    
    return render(request, 'tienda/producto_detalle.html', {
        'producto': producto,
        'stock': stock,
        'color': color,
        'categoria_nombre': cat_nombre,
    })


@login_required_user
def carrito_view(request):
    carrito = request.session.get('carrito', {})
    items = []
    total = Decimal('0')
    
    for prod_id, cantidad in carrito.items():
        try:
            producto = Producto.objects.get(pk=int(prod_id))
            subtotal = producto.producto_precio_venta * cantidad
            total += subtotal
            items.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal,
            })
        except Producto.DoesNotExist:
            pass
    
    return render(request, 'tienda/carrito.html', {
        'items': items,
        'total': total,
        'total_formateado': f"${total:,.0f}",
    })


@login_required_user
def carrito_agregar(request, pk):
    if request.method == 'POST':
        carrito = request.session.get('carrito', {})
        pk_str = str(pk)
        cantidad = int(request.POST.get('cantidad', 1))
        
        try:
            inventario = Inventario.objects.get(producto_id=pk)
            stock_disp = inventario.inventario_stock_actual or 0
        except Inventario.DoesNotExist:
            stock_disp = 0
        
        actual = carrito.get(pk_str, 0)
        nuevo = actual + cantidad
        
        if nuevo > stock_disp:
            messages.error(request, f'Stock insuficiente. Disponible: {stock_disp}')
        else:
            carrito[pk_str] = nuevo
            request.session['carrito'] = carrito
            messages.success(request, 'Producto agregado al carrito.')
    
    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required_user
def carrito_eliminar(request, pk):
    carrito = request.session.get('carrito', {})
    pk_str = str(pk)
    if pk_str in carrito:
        del carrito[pk_str]
        request.session['carrito'] = carrito
        messages.success(request, 'Producto eliminado del carrito.')
    return redirect('/carrito/')


@login_required_user
def carrito_actualizar(request, pk):
    if request.method == 'POST':
        carrito = request.session.get('carrito', {})
        pk_str = str(pk)
        cantidad = int(request.POST.get('cantidad', 1))
        
        if cantidad <= 0:
            if pk_str in carrito:
                del carrito[pk_str]
        else:
            carrito[pk_str] = cantidad
        
        request.session['carrito'] = carrito
    return redirect('/carrito/')


@login_required_user
def checkout(request):
    carrito = request.session.get('carrito', {})
    if not carrito:
        messages.error(request, 'Tu carrito está vacío.')
        return redirect('/carrito/')
    
    user_id = request.session.get('user_id')
    metodos_pago = MetodoPago.objects.all()
    
    # Try to get existing cliente for pre-filling
    try:
        cliente = Cliente.objects.get(user_id=user_id)
    except Cliente.DoesNotExist:
        cliente = None
    
    items = []
    total = Decimal('0')
    for prod_id, cantidad in carrito.items():
        try:
            producto = Producto.objects.get(pk=int(prod_id))
            subtotal = producto.producto_precio_venta * cantidad
            total += subtotal
            items.append({
                'producto': producto,
                'cantidad': cantidad,
                'subtotal': subtotal,
            })
        except Producto.DoesNotExist:
            pass
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '')
        email = request.POST.get('email', '')
        telefono = request.POST.get('telefono', '')
        documento = request.POST.get('documento', '')
        direccion = request.POST.get('direccion', '')
        metodo_pago_id = request.POST.get('metodo_pago')
        observaciones = request.POST.get('observaciones', '')
        
        # Create or update cliente
        if cliente:
            cliente.cliente_nombre = nombre
            cliente.cliente_email = email
            cliente.cliente_telefono = telefono
            cliente.cliente_numero_documento = documento
            cliente.cliente_direccion = direccion
            cliente.save()
        else:
            cliente = Cliente.objects.create(
                user_id=user_id,
                cliente_nombre=nombre,
                cliente_email=email,
                cliente_telefono=telefono,
                cliente_numero_documento=documento,
                cliente_direccion=direccion,
            )
        
        venta = Venta.objects.create(
            venta_fecha=date.today(),
            venta_hora=datetime.now().time(),
            venta_total=total,
            user_id=user_id,
            cliente=cliente,
            metodo_pago_id=metodo_pago_id,
            observaciones=observaciones,
        )
        
        for item in items:
            VentaDetalle.objects.create(
                venta=venta,
                producto=item['producto'],
                venta_detalle_cantidad=item['cantidad'],
                venta_detalle_precio_venta=item['producto'].producto_precio_venta,
                subtotal=item['subtotal'],
            )
            
            MovimientoInventario.objects.create(
                producto=item['producto'],
                movimiento_tipo='SALIDA',
                movimiento_cantidad=item['cantidad'],
                movimiento_fecha=date.today(),
                movimiento_motivo='Venta realizada',
            )
        
        request.session['carrito'] = {}
        messages.success(request, f'¡Compra realizada! Código: #{venta.venta_codigo}')
        return redirect('/pedidos/')
    
    return render(request, 'tienda/checkout.html', {
        'items': items,
        'total': total,
        'total_formateado': f"${total:,.0f}",
        'metodos_pago': metodos_pago,
        'cliente': cliente,
    })


@login_required_user
def pedidos(request):
    user_id = request.session.get('user_id')
    ventas = Venta.objects.filter(user_id=user_id).select_related('metodo_pago').order_by('-venta_fecha', '-venta_hora')
    return render(request, 'tienda/pedidos.html', {'ventas': ventas})


@login_required_user
def pedido_detalle(request, pk):
    user_id = request.session.get('user_id')
    venta = get_object_or_404(Venta, pk=pk, user_id=user_id)
    detalles = VentaDetalle.objects.filter(venta=venta).select_related('producto')
    return render(request, 'tienda/pedido_detalle.html', {
        'venta': venta,
        'detalles': detalles,
        'total_formateado': f"${venta.venta_total:,.0f}",
    })


@login_required_user
def perfil(request):
    user_id = request.session.get('user_id')
    user = get_object_or_404(User, pk=user_id)
    
    try:
        cliente = Cliente.objects.get(user_id=user_id)
    except Cliente.DoesNotExist:
        cliente = None
    
    if request.method == 'POST':
        user.name = request.POST.get('name', '')
        user.save()
        
        if cliente:
            cliente.cliente_nombre = request.POST.get('name', '')
            cliente.cliente_telefono = request.POST.get('telefono', '')
            cliente.cliente_direccion = request.POST.get('direccion', '')
            cliente.cliente_numero_documento = request.POST.get('documento', '')
            cliente.save()
        
        request.session['user_name'] = user.name
        messages.success(request, 'Perfil actualizado.')
        return redirect('/perfil/')
    
    return render(request, 'tienda/perfil.html', {
        'user': user,
        'cliente': cliente,
    })
