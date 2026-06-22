from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.models import (
    Producto, Categoria, Inventario, Venta, VentaDetalle,
    MetodoPago, MovimientoInventario, ProductoAtributo, User
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
    from django.core.cache import cache
    productos = cache.get('home_productos')
    if productos is None:
        productos = list(Producto.objects.filter(producto_estado='Activo').select_related('categoria').order_by('producto_id')[:6])
        cache.set('home_productos', productos, 300)
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
        try:
            productos = productos.filter(producto_precio_venta__gte=float(precio_min))
        except ValueError:
            pass
    if precio_max:
        try:
            productos = productos.filter(producto_precio_venta__lte=float(precio_max))
        except ValueError:
            pass
    
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
    user = get_object_or_404(User, pk=user_id)
    metodos_pago = MetodoPago.objects.all()
    
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
        # Rate limit: 1 compra cada 20 segundos
        last_purchase = request.session.get('last_purchase_time')
        now = datetime.now().timestamp()
        if last_purchase and (now - last_purchase) < 20:
            messages.error(request, 'Por favor, espera 20 segundos entre cada intento de compra.')
            return redirect('/pedidos/')

        nombre = request.POST.get('nombre', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        documento = request.POST.get('documento', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        metodo_pago_id = request.POST.get('metodo_pago')
        observaciones = request.POST.get('observaciones', '')
        es_regalo = request.POST.get('es_regalo') == '1'
        
        # Validaciones de Backend
        errors = []
        if es_regalo:
            dest_nombre = request.POST.get('destinatario_nombre', '').strip()
            dest_telefono = request.POST.get('destinatario_telefono', '').strip()
            dest_direccion = request.POST.get('destinatario_direccion', '').strip()
            mensaje = request.POST.get('mensaje_regalo', '')
            
            if not dest_nombre or len(dest_nombre) < 4:
                errors.append("El nombre del destinatario debe tener al menos 4 caracteres.")
            if not dest_telefono or not dest_telefono.isdigit() or len(dest_telefono) != 10:
                errors.append("El teléfono del destinatario debe tener exactamente 10 dígitos.")
            if not dest_direccion or len(dest_direccion) < 5 or not any(c.isdigit() for c in dest_direccion):
                errors.append("La dirección del destinatario debe tener al menos 5 caracteres y contener al menos un número.")
            
            obs_regalo = f"[REGALO] Para: {dest_nombre} | Tel: {dest_telefono} | Dir: {dest_direccion}"
            if mensaje:
                obs_regalo += f" | Mensaje: {mensaje}"
            observaciones = f"{obs_regalo}\n{observaciones}".strip()
        else:
            if not telefono or not telefono.isdigit() or len(telefono) != 10:
                errors.append("El teléfono debe tener exactamente 10 dígitos.")
            if not documento or not documento.isdigit() or not (6 <= len(documento) <= 12):
                errors.append("El documento debe tener entre 6 y 12 dígitos.")
            if not direccion or len(direccion) < 5 or not any(c.isdigit() for c in direccion):
                errors.append("La dirección debe tener al menos 5 caracteres y contener al menos un número.")
                
        if not metodo_pago_id:
            errors.append("Debes seleccionar un método de pago.")
            
        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'tienda/checkout.html', {
                'items': items,
                'total': total,
                'total_formateado': f"${total:,.0f}",
                'metodos_pago': metodos_pago,
                'user': user,
            })
            
        if not es_regalo:
            user.telefono = telefono
            user.numero_documento = documento
            user.direccion = direccion
            user.save()
            
        # Registrar el tiempo de la compra para el rate limit
        request.session['last_purchase_time'] = datetime.now().timestamp()
        
        venta = Venta.objects.create(
            venta_fecha=date.today(),
            venta_hora=datetime.now().time(),
            venta_total=total,
            user_id=user_id,
            comprador_id=user_id,
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
            
            # Actualizar inventario
            try:
                inventario = Inventario.objects.get(producto=item['producto'])
                stock_anterior = inventario.inventario_stock_actual or 0
                stock_nuevo = stock_anterior - item['cantidad']
                inventario.inventario_stock_actual = stock_nuevo
                inventario.save()
            except Inventario.DoesNotExist:
                stock_anterior = 0
                stock_nuevo = -item['cantidad']
                
            MovimientoInventario.objects.create(
                producto=item['producto'],
                movimiento_tipo='SALIDA',
                movimiento_cantidad=item['cantidad'],
                movimiento_fecha=date.today(),
                movimiento_motivo='Venta realizada',
                movimiento_stock_anterior=stock_anterior,
                movimiento_stock_nuevo=stock_nuevo,
            )
        
        # Enviar correo de confirmación en segundo plano (no bloquea la respuesta)
        import threading
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings

        protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        base_url = f"{protocol}://{host}"

        ctx = {
            'nombre': user.name,
            'venta_codigo': venta.venta_codigo,
            'es_regalo': es_regalo,
            'items': items,
            'total': total,
            'base_url': base_url,
        }

        if es_regalo:
            ctx.update({
                'dest_nombre': dest_nombre,
                'dest_telefono': dest_telefono,
                'dest_direccion': dest_direccion,
                'mensaje_regalo': mensaje,
            })
        else:
            ctx.update({
                'telefono': user.telefono,
                'direccion': user.direccion,
            })

        def _send_email():
            try:
                html_message = render_to_string('tienda/email_compra.html', ctx)
                plain_message = strip_tags(html_message)
                print(f"[MAIL] Intentando enviar correo de confirmación a {user.email}...")
                send_mail(
                    subject=f"Confirmación de Compra #{venta.venta_codigo} - FH TechStore",
                    message=plain_message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@fh.com'),
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                print(f"[MAIL] Correo enviado exitosamente a {user.email}.")
            except Exception as e:
                print(f"[MAIL ERROR] Falló el envío a {user.email}: {str(e)}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=_send_email, daemon=True).start()

        request.session['carrito'] = {}
        messages.success(request, f'¡Compra realizada! Código: #{venta.venta_codigo}. Se ha enviado un correo de confirmación.')
        return redirect('/pedidos/')
    
    return render(request, 'tienda/checkout.html', {
        'items': items,
        'total': total,
        'total_formateado': f"${total:,.0f}",
        'metodos_pago': metodos_pago,
        'user': user,
    })


@login_required_user
def pedidos(request):
    user_id = request.session.get('user_id')
    ventas = Venta.objects.filter(comprador_id=user_id).select_related('metodo_pago').order_by('-venta_fecha', '-venta_hora')
    return render(request, 'tienda/pedidos.html', {'ventas': ventas})


@login_required_user
def pedido_detalle(request, pk):
    user_id = request.session.get('user_id')
    venta = get_object_or_404(Venta, pk=pk, comprador_id=user_id)
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
    
    if request.method == 'POST':
        user.name = request.POST.get('name', '')
        user.telefono = request.POST.get('telefono', '')
        user.direccion = request.POST.get('direccion', '')
        user.numero_documento = request.POST.get('documento', '')
        user.save()
        
        request.session['user_name'] = user.name
        messages.success(request, 'Perfil actualizado.')
        return redirect('/perfil/')
    
    return render(request, 'tienda/perfil.html', {
        'user': user,
    })
