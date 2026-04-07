from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import (
    User, Producto, Categoria, Inventario, Venta, VentaDetalle,
    Cliente, MovimientoInventario, MetodoPago, AtributoValor, ProductoAtributo
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


@admin_required
def dashboard(request):
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
    
    ultimas_ventas = Venta.objects.select_related('cliente', 'user', 'metodo_pago').order_by('-venta_fecha', '-venta_hora')[:5]
    
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
        
        # Manejar upload de imagen
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
        
        # Manejar foto: si hay archivo, se sube; si no, se mantiene la actual
        foto = request.POST.get('foto', '')
        if foto and 'imagenFile' not in request.FILES:
            producto.foto = foto
        producto.save()
        
        # Manejar upload de imagen
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
        
        # Verificar si ya existe
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
        MovimientoInventario.objects.create(
            producto_id=request.POST.get('producto'),
            movimiento_tipo=request.POST.get('tipo'),
            movimiento_cantidad=int(request.POST.get('cantidad', 0)),
            movimiento_fecha=date.today(),
            movimiento_motivo=request.POST.get('motivo', ''),
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
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Este correo ya existe.')
            return render(request, 'admin_panel/usuario_form.html', {
                'titulo': 'Crear Usuario', 'name': name, 'email': email, 'role': role
            })
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        User.objects.create(
            name=name, email=email, password=hashed,
            role=role, enabled=True,
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
def usuario_delete(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado.')
    return redirect('/panel/usuarios/')


# ======================== VENTAS ========================

@admin_required
def ventas_list(request):
    ventas = Venta.objects.select_related('cliente', 'user', 'metodo_pago').all().order_by('-venta_fecha', '-venta_hora')
    return render(request, 'admin_panel/ventas.html', {'ventas': ventas})


@admin_required
def venta_detalle_view(request, pk):
    venta = get_object_or_404(Venta, pk=pk)
    detalles = VentaDetalle.objects.filter(venta=venta).select_related('producto')
    return render(request, 'admin_panel/venta_detalle.html', {
        'venta': venta,
        'detalles': detalles,
    })


# ======================== CLIENTES ========================

@admin_required
def clientes_list(request):
    clientes = Cliente.objects.select_related('user').all().order_by('cliente_id')
    return render(request, 'admin_panel/clientes.html', {'clientes': clientes})


@admin_required
def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.cliente_nombre = request.POST.get('nombre', '')
        cliente.cliente_numero_documento = request.POST.get('documento', '')
        cliente.cliente_telefono = request.POST.get('telefono', '')
        cliente.cliente_email = request.POST.get('email', '')
        cliente.cliente_direccion = request.POST.get('direccion', '')
        cliente.save()
        messages.success(request, 'Cliente actualizado.')
        return redirect('/panel/clientes/')
    return render(request, 'admin_panel/cliente_form.html', {
        'cliente': cliente, 'titulo': 'Editar Cliente'
    })
