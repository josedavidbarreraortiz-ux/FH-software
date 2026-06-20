from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import (
    User, Producto, Categoria, Inventario, Venta, VentaDetalle,
    MovimientoInventario, MetodoPago, AtributoValor, ProductoAtributo
)
from functools import wraps
from datetime import date, datetime
import bcrypt
import os
from django.conf import settings as django_settings


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_role = request.session.get('user_role')
        if not user_id or user_role != 'ADMIN':
            messages.error(request, 'Acceso denegado. Se requiere rol de administrador.')
            return redirect('/accounts/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Permite acceso a ADMIN y VENDEDOR."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        user_role = request.session.get('user_role')
        if not user_id or user_role not in ('ADMIN', 'VENDEDOR'):
            messages.error(request, 'Acceso denegado.')
            return redirect('/accounts/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_marcas():
    """Obtiene lista de marcas únicas existentes."""
    marcas = Producto.objects.exclude(
        producto_marca__isnull=True
    ).exclude(
        producto_marca=''
    ).values_list('producto_marca', flat=True).distinct().order_by('producto_marca')
    return list(marcas)


def _handle_imagen_upload(request, producto):
    """Maneja la subida de imagen del producto."""
    if 'imagenFile' in request.FILES:
        imagen = request.FILES['imagenFile']
        upload_dir = os.path.join(django_settings.MEDIA_ROOT, 'uploads', 'productos')
        os.makedirs(upload_dir, exist_ok=True)

        # Generar nombre único
        ext = os.path.splitext(imagen.name)[1].lower()
        filename = f"producto_{producto.producto_id}_{int(datetime.now().timestamp())}{ext}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as f:
            for chunk in imagen.chunks():
                f.write(chunk)

        producto.foto = filename
        producto.save()


@staff_required
def dashboard(request):
    user_role = request.session.get('user_role')
    
    # VENDEDOR solo ve dashboard de ventas
    if user_role == 'VENDEDOR':
        return vendedor_dashboard(request)
    
    total_productos = Producto.objects.count()
    total_categorias = Categoria.objects.count()
    total_usuarios = User.objects.count()
    total_ventas = Venta.objects.count()
    ventas_hoy = Venta.objects.filter(venta_fecha=date.today()).count()
    
    from django.db.models import Sum
    ingresos_total = Venta.objects.aggregate(total=Sum('venta_total'))['total'] or 0
    
    from django.db.models import F
    try:
        stock_bajo = Inventario.objects.filter(
            inventario_stock_actual__lte=F('inventario_stock_minimo')
        ).count()
    except:
        stock_bajo = 0
    
    ultimas_ventas = Venta.objects.select_related('comprador', 'user', 'metodo_pago').order_by('-venta_fecha', '-venta_hora')[:5]
    
    context = {
        'total_productos': total_productos,
        'total_categorias': total_categorias,
        'total_usuarios': total_usuarios,
        'total_ventas': total_ventas,
        'ventas_hoy': ventas_hoy,
        'ingresos_total': f"${ingresos_total:,.0f}" if ingresos_total else "$0",
        'stock_bajo': stock_bajo,
        'ultimas_ventas': ultimas_ventas,
    }
    return render(request, 'admin_panel/dashboard.html', context)


def vendedor_dashboard(request):
    """Dashboard limitado para vendedores: solo info de ventas."""
    from django.db.models import Sum
    
    total_ventas = Venta.objects.count()
    ventas_hoy = Venta.objects.filter(venta_fecha=date.today()).count()
    ingresos_total = Venta.objects.aggregate(total=Sum('venta_total'))['total'] or 0
    
    # Ventas del vendedor actual
    user_id = request.session.get('user_id')
    mis_ventas = Venta.objects.filter(user_id=user_id).count()
    
    ultimas_ventas = Venta.objects.select_related(
        'comprador', 'user', 'metodo_pago'
    ).order_by('-venta_fecha', '-venta_hora')[:10]
    
    context = {
        'total_ventas': total_ventas,
        'ventas_hoy': ventas_hoy,
        'ingresos_total': f"${ingresos_total:,.0f}" if ingresos_total else "$0",
        'mis_ventas': mis_ventas,
        'ultimas_ventas': ultimas_ventas,
    }
    return render(request, 'admin_panel/dashboard_vendedor.html', context)


# ======================== PRODUCTOS ========================

@admin_required
def productos_list(request):
    productos = Producto.objects.select_related('categoria').all().order_by('producto_id')
    categorias = Categoria.objects.filter(estado=1)
    return render(request, 'admin_panel/productos.html', {
        'productos': productos,
        'categorias': categorias,
    })


@admin_required
def producto_show(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    try:
        producto_attr = ProductoAtributo.objects.get(producto=producto)
        color_nombre = producto_attr.valor.valor if producto_attr.valor else None
    except ProductoAtributo.DoesNotExist:
        color_nombre = None
    
    try:
        inventario = Inventario.objects.get(producto=producto)
    except Inventario.DoesNotExist:
        inventario = None
    
    return render(request, 'admin_panel/producto_detalle.html', {
        'producto': producto,
        'color_nombre': color_nombre,
        'inventario': inventario,
    })


@admin_required
def producto_create(request):
    categorias = Categoria.objects.filter(estado=1)
    colores = AtributoValor.objects.filter(atributo_id=1)
    marcas = _get_marcas()
    
    if request.method == 'POST':
        producto = Producto.objects.create(
            producto_nombre=request.POST.get('nombre', ''),
            producto_codigo_bar=request.POST.get('codigo', ''),
            producto_marca=request.POST.get('marca', ''),
            producto_precio_venta=request.POST.get('precio', 0),
            tipo_unidad=request.POST.get('unidad', 'Unidad'),
            categoria_id=request.POST.get('categoria') or None,
            especificacion=request.POST.get('especificacion', ''),
            resumen=request.POST.get('resumen', ''),
            producto_estado=request.POST.get('estado', 'Activo'),
            foto=request.POST.get('foto', ''),
        )
        
        _handle_imagen_upload(request, producto)
        
        color_id = request.POST.get('color')
        if color_id:
            ProductoAtributo.objects.create(
                producto=producto,
                atributo_id=1,
                valor_id=color_id
            )
        
        stock_actual = request.POST.get('stock_actual', 0)
        stock_min = request.POST.get('stock_minimo', 0)
        stock_max = request.POST.get('stock_maximo', 0)
        ubicacion = request.POST.get('ubicacion', '')
        
        Inventario.objects.create(
            producto=producto,
            inventario_stock_actual=int(stock_actual) if stock_actual else 0,
            inventario_stock_minimo=int(stock_min) if stock_min else 0,
            inventario_stock_maximo=int(stock_max) if stock_max else 0,
            inventario_ubicacion=ubicacion,
        )
        
        messages.success(request, f'Producto "{producto.producto_nombre}" creado exitosamente.')
        return redirect('/panel/productos/')
    
    return render(request, 'admin_panel/producto_form.html', {
        'categorias': categorias,
        'colores': colores,
        'marcas': marcas,
        'titulo': 'Crear Producto',
    })


@admin_required
def producto_edit(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    categorias = Categoria.objects.filter(estado=1)
    colores = AtributoValor.objects.filter(atributo_id=1)
    marcas = _get_marcas()
    
    try:
        producto_attr = ProductoAtributo.objects.get(producto=producto)
        color_actual = producto_attr.valor_id if producto_attr.valor else None
    except ProductoAtributo.DoesNotExist:
        color_actual = None
    
    try:
        inventario = Inventario.objects.get(producto=producto)
    except Inventario.DoesNotExist:
        inventario = None
    
    if request.method == 'POST':
        producto.producto_nombre = request.POST.get('nombre', '')
        producto.producto_codigo_bar = request.POST.get('codigo', '')
        producto.producto_marca = request.POST.get('marca', '')
        precio_nuevo = request.POST.get('precio', '').strip()
        if precio_nuevo:
            producto.producto_precio_venta = precio_nuevo
        producto.tipo_unidad = request.POST.get('unidad', 'Unidad')
        producto.categoria_id = request.POST.get('categoria') or None
        producto.especificacion = request.POST.get('especificacion', '')
        producto.resumen = request.POST.get('resumen', '')
        producto.producto_estado = request.POST.get('estado', 'Activo')
        
        foto = request.POST.get('foto', '')
        if foto and 'imagenFile' not in request.FILES:
            producto.foto = foto
        producto.save()
        
        _handle_imagen_upload(request, producto)
        
        color_id = request.POST.get('color')
        if color_id:
            ProductoAtributo.objects.update_or_create(
                producto=producto,
                atributo_id=1,
                defaults={'valor_id': color_id}
            )
        
        if inventario:
            inventario.inventario_stock_actual = int(request.POST.get('stock_actual', 0) or 0)
            inventario.inventario_stock_minimo = int(request.POST.get('stock_minimo', 0) or 0)
            inventario.inventario_stock_maximo = int(request.POST.get('stock_maximo', 0) or 0)
            inventario.inventario_ubicacion = request.POST.get('ubicacion', '')
            inventario.save()
        
        messages.success(request, f'Producto "{producto.producto_nombre}" actualizado.')
        return redirect('/panel/productos/')
    
    return render(request, 'admin_panel/producto_form.html', {
        'producto': producto,
        'categorias': categorias,
        'colores': colores,
        'marcas': marcas,
        'color_actual': color_actual,
        'inventario': inventario,
        'titulo': 'Editar Producto',
    })


@admin_required
def producto_delete(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        nombre = producto.producto_nombre
        ProductoAtributo.objects.filter(producto=producto).delete()
        Inventario.objects.filter(producto=producto).delete()
        producto.delete()
        messages.success(request, f'Producto "{nombre}" eliminado.')
    return redirect('/panel/productos/')


@admin_required
def color_nuevo(request):
    """Endpoint AJAX para crear un nuevo color."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            return JsonResponse({'success': False, 'mensaje': 'El nombre del color es requerido'})
        
        if AtributoValor.objects.filter(atributo_id=1, valor__iexact=nombre).exists():
            return JsonResponse({'success': False, 'mensaje': 'Este color ya existe'})
        
        nuevo_color = AtributoValor.objects.create(
            atributo_id=1,
            valor=nombre
        )
        return JsonResponse({
            'success': True,
            'valor_id': nuevo_color.valor_id,
            'valor': nuevo_color.valor
        })
    return JsonResponse({'success': False, 'mensaje': 'Método no permitido'})


# ======================== CATEGORÍAS ========================

@admin_required
def categorias_list(request):
    categorias = Categoria.objects.all().order_by('categoria_id')
    return render(request, 'admin_panel/categorias.html', {'categorias': categorias})


@admin_required
def categoria_create(request):
    if request.method == 'POST':
        Categoria.objects.create(
            categoria_nombre=request.POST.get('nombre', ''),
            descripcion=request.POST.get('descripcion', ''),
            estado=int(request.POST.get('estado', 1)),
        )
        messages.success(request, 'Categoría creada exitosamente.')
        return redirect('/panel/categorias/')
    return render(request, 'admin_panel/categoria_form.html', {'titulo': 'Crear Categoría'})


@admin_required
def categoria_edit(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.categoria_nombre = request.POST.get('nombre', '')
        categoria.descripcion = request.POST.get('descripcion', '')
        categoria.estado = int(request.POST.get('estado', 1))
        categoria.save()
        messages.success(request, 'Categoría actualizada.')
        return redirect('/panel/categorias/')
    return render(request, 'admin_panel/categoria_form.html', {
        'categoria': categoria,
        'titulo': 'Editar Categoría',
    })


@admin_required
def categoria_delete(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        categoria.delete()
        messages.success(request, 'Categoría eliminada.')
    return redirect('/panel/categorias/')


# ======================== INVENTARIO ========================

@admin_required
def inventario_list(request):
    inventarios = Inventario.objects.select_related('producto').all().order_by('inventario_id')
    return render(request, 'admin_panel/inventario.html', {'inventarios': inventarios})


@admin_required
def inventario_edit(request, pk):
    inventario = get_object_or_404(Inventario, pk=pk)
    if request.method == 'POST':
        inventario.inventario_stock_actual = int(request.POST.get('stock_actual', 0) or 0)
        inventario.inventario_stock_minimo = int(request.POST.get('stock_minimo', 0) or 0)
        inventario.inventario_stock_maximo = int(request.POST.get('stock_maximo', 0) or 0)
        inventario.inventario_ubicacion = request.POST.get('ubicacion', '')
        inventario.observaciones = request.POST.get('observaciones', '')
        inventario.save()
        messages.success(request, 'Inventario actualizado.')
        return redirect('/panel/inventario/')
    return render(request, 'admin_panel/inventario_form.html', {
        'inventario': inventario,
        'titulo': 'Editar Inventario',
    })


@admin_required
def movimientos_list(request):
    movimientos = MovimientoInventario.objects.select_related('producto').all().order_by('-movimiento_fecha', '-movimiento_id')
    return render(request, 'admin_panel/movimientos.html', {'movimientos': movimientos})


@admin_required
def movimiento_create(request):
    productos = Producto.objects.all().order_by('producto_nombre')
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        tipo = request.POST.get('tipo')
        cantidad = int(request.POST.get('cantidad', 0))
        motivo = request.POST.get('motivo', '')
        
        # Actualizar inventario
        try:
            inventario = Inventario.objects.get(producto_id=producto_id)
            stock_anterior = inventario.inventario_stock_actual or 0
            if tipo == 'ENTRADA':
                stock_nuevo = stock_anterior + cantidad
            else:
                stock_nuevo = stock_anterior - cantidad
            inventario.inventario_stock_actual = stock_nuevo
            inventario.save()
        except Inventario.DoesNotExist:
            stock_anterior = 0
            if tipo == 'ENTRADA':
                stock_nuevo = cantidad
            else:
                stock_nuevo = -cantidad
                
        MovimientoInventario.objects.create(
            producto_id=producto_id,
            movimiento_tipo=tipo,
            movimiento_cantidad=cantidad,
            movimiento_fecha=date.today(),
            movimiento_motivo=motivo,
            movimiento_stock_anterior=stock_anterior,
            movimiento_stock_nuevo=stock_nuevo,
        )
        messages.success(request, 'Movimiento registrado.')
        return redirect('/panel/movimientos/')
    return render(request, 'admin_panel/movimiento_form.html', {
        'productos': productos,
        'titulo': 'Registrar Movimiento',
    })


# ======================== USUARIOS ========================

@admin_required
def usuarios_list(request):
    usuarios = User.objects.all().order_by('id')
    return render(request, 'admin_panel/usuarios.html', {'usuarios': usuarios})


@admin_required
def usuario_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'USER')
        telefono = request.POST.get('telefono', '')
        direccion = request.POST.get('direccion', '')
        numero_documento = request.POST.get('numero_documento', '')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este correo ya existe.')
            return render(request, 'admin_panel/usuario_form.html', {
                'titulo': 'Crear Usuario', 'name': name, 'email': email, 'role': role
            })
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        User.objects.create(
            name=name, email=email, password=hashed,
            role=role, enabled=True,
            telefono=telefono, direccion=direccion, numero_documento=numero_documento,
            created_at=datetime.now(), updated_at=datetime.now()
        )
        messages.success(request, f'Usuario "{name}" creado.')
        return redirect('/panel/usuarios/')
    return render(request, 'admin_panel/usuario_form.html', {'titulo': 'Crear Usuario'})


@admin_required
def usuario_edit(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        usuario.name = request.POST.get('name', '')
        usuario.email = request.POST.get('email', '')
        usuario.role = request.POST.get('role', 'USER')
        usuario.enabled = request.POST.get('enabled') == 'on'
        usuario.telefono = request.POST.get('telefono', '')
        usuario.direccion = request.POST.get('direccion', '')
        usuario.numero_documento = request.POST.get('numero_documento', '')
        
        password = request.POST.get('password', '')
        if password:
            usuario.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        usuario.updated_at = datetime.now()
        usuario.save()
        messages.success(request, f'Usuario "{usuario.name}" actualizado.')
        return redirect('/panel/usuarios/')
    return render(request, 'admin_panel/usuario_form.html', {
        'usuario': usuario, 'titulo': 'Editar Usuario'
    })


@admin_required
def usuario_send_reset(request, pk):
    from accounts.views import _generate_token, _hash_token, _send_reset_email
    
    usuario = get_object_or_404(User, pk=pk, enabled=True)
    try:
        raw_token = _generate_token()
        token_data = f"{int(datetime.now().timestamp())}|{_hash_token(raw_token)}"
        usuario.remember_token = token_data
        usuario.updated_at = datetime.now()
        usuario.save(update_fields=['remember_token', 'updated_at'])

        protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        reset_url = f"{protocol}://{host}/accounts/password-reset/confirm/{usuario.id}/{raw_token}/"

        _send_reset_email(usuario, reset_url)
        messages.success(request, f'Enlace de recuperación enviado al correo {usuario.email}.')
    except Exception as e:
        messages.error(request, 'Hubo un error al enviar el enlace de recuperación.')
        
    return redirect(f'/panel/usuarios/{pk}/editar/')


@admin_required
def usuario_delete(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado.')
    return redirect('/panel/usuarios/')


# ======================== VENTAS ========================

@staff_required
def ventas_list(request):
    ventas = Venta.objects.select_related('comprador', 'user', 'metodo_pago').all().order_by('-venta_fecha', '-venta_hora')
    return render(request, 'admin_panel/ventas.html', {'ventas': ventas})


@staff_required
def venta_detalle_view(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    detalles = VentaDetalle.objects.filter(venta=venta).select_related('producto')
    return render(request, 'admin_panel/venta_detalle.html', {
        'venta': venta,
        'detalles': detalles,
    })


@staff_required
def venta_create(request):
    """Registrar una nueva venta desde el panel (ADMIN o VENDEDOR)."""
    from decimal import Decimal
    import json

    productos = Producto.objects.filter(producto_estado='Activo').select_related('categoria').order_by('producto_nombre')
    usuarios = User.objects.filter(enabled=True, role='USER').order_by('name')
    metodos_pago = MetodoPago.objects.all()

    if request.method == 'POST':
        comprador_id = request.POST.get('comprador_id')
        metodo_pago_id = request.POST.get('metodo_pago')
        observaciones = request.POST.get('observaciones', '')
        items_json = request.POST.get('items_json', '[]')

        try:
            items = json.loads(items_json)
        except (json.JSONDecodeError, TypeError):
            messages.error(request, 'Error en los datos de productos.')
            return redirect('/panel/ventas/nueva/')

        if not items:
            messages.error(request, 'Debes agregar al menos un producto.')
            return redirect('/panel/ventas/nueva/')

        es_venta_local = request.POST.get('es_venta_local') == '1'

        if es_venta_local:
            local_nombre = request.POST.get('local_nombre', '').strip()
            local_documento = request.POST.get('local_documento', '').strip()
            
            if not local_nombre or not local_documento:
                messages.error(request, 'Debes ingresar el nombre y documento para venta rápida.')
                return redirect('/panel/ventas/nueva/')
                
            comprador = User.objects.filter(numero_documento=local_documento).first()
            if not comprador:
                import time
                dummy_email = f"local_{local_documento}_{int(time.time())}@local.fh"
                hashed = bcrypt.hashpw('localpassword'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                comprador = User.objects.create(
                    name=local_nombre,
                    numero_documento=local_documento,
                    email=dummy_email,
                    password=hashed,
                    role='USER',
                    enabled=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            comprador_id = comprador.id
        elif not comprador_id:
            messages.error(request, 'Debes seleccionar un comprador.')
            return redirect('/panel/ventas/nueva/')
        else:
            comprador = User.objects.get(pk=comprador_id)
            direccion_envio = request.POST.get('direccion_envio', '').strip()
            if direccion_envio:
                comprador.direccion = direccion_envio
                comprador.updated_at = datetime.now()
                comprador.save()
        # Calcular total
        total = Decimal('0')
        detalles_data = []
        for item in items:
            try:
                producto = Producto.objects.get(pk=int(item['producto_id']))
                cantidad = int(item['cantidad'])
                precio = producto.producto_precio_venta
                subtotal = precio * cantidad
                total += subtotal
                detalles_data.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'precio': precio,
                    'subtotal': subtotal,
                })
            except (Producto.DoesNotExist, ValueError, KeyError):
                continue

        if not detalles_data:
            messages.error(request, 'No se pudieron procesar los productos.')
            return redirect('/panel/ventas/nueva/')

        user_id = request.session.get('user_id')

        venta = Venta.objects.create(
            venta_fecha=date.today(),
            venta_hora=datetime.now().time(),
            venta_total=total,
            user_id=user_id,
            comprador_id=comprador_id,
            metodo_pago_id=metodo_pago_id,
            observaciones=observaciones,
        )

        for det in detalles_data:
            VentaDetalle.objects.create(
                venta=venta,
                producto=det['producto'],
                venta_detalle_cantidad=det['cantidad'],
                venta_detalle_precio_venta=det['precio'],
                subtotal=det['subtotal'],
            )
            
            # Actualizar inventario
            try:
                inventario = Inventario.objects.get(producto=det['producto'])
                stock_anterior = inventario.inventario_stock_actual or 0
                stock_nuevo = stock_anterior - det['cantidad']
                inventario.inventario_stock_actual = stock_nuevo
                inventario.save()
            except Inventario.DoesNotExist:
                stock_anterior = 0
                stock_nuevo = -det['cantidad']
                
            MovimientoInventario.objects.create(
                producto=det['producto'],
                movimiento_tipo='SALIDA',
                movimiento_cantidad=det['cantidad'],
                movimiento_fecha=date.today(),
                movimiento_motivo='Venta realizada',
                movimiento_stock_anterior=stock_anterior,
                movimiento_stock_nuevo=stock_nuevo,
            )

        messages.success(request, f'Venta #{venta.venta_codigo} registrada exitosamente. Total: ${total:,.0f}')
        return redirect('/panel/ventas/')

    # Preparar datos de productos como JSON para el JS
    productos_data = []
    for p in productos:
        try:
            inv = Inventario.objects.get(producto=p)
            stock = inv.inventario_stock_actual or 0
        except Inventario.DoesNotExist:
            stock = 0
        productos_data.append({
            'id': p.producto_id,
            'nombre': p.producto_nombre,
            'precio': float(p.producto_precio_venta) if p.producto_precio_venta else 0,
            'marca': p.producto_marca or '',
            'stock': stock,
        })

    import json as json_mod
    return render(request, 'admin_panel/venta_form.html', {
        'productos': productos,
        'productos_json': json_mod.dumps(productos_data),
        'usuarios': usuarios,
        'metodos_pago': metodos_pago,
        'titulo': 'Registrar Venta',
    })
