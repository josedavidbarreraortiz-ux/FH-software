from django.db import models


class User(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(max_length=255, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=255)
    remember_token = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    enabled = models.BooleanField(default=True, null=True, blank=True)
    role = models.CharField(max_length=255, null=True, blank=True)
    telefono = models.CharField(max_length=255, null=True, blank=True)
    direccion = models.CharField(max_length=255, null=True, blank=True)
    numero_documento = models.CharField(max_length=255, null=True, blank=True)
    tipo_documento = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if isinstance(self.enabled, bytes):
            self.enabled = self.enabled == b'\x01'
        super().save(*args, **kwargs)

    @property
    def is_admin(self):
        return self.role == 'ADMIN'

    @property
    def is_vendedor(self):
        return self.role == 'VENDEDOR'


class Categoria(models.Model):
    categoria_id = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='parent_id')
    categoria_nombre = models.CharField(max_length=255, null=True, blank=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    estado = models.IntegerField(default=1, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'categoria'

    def __str__(self):
        return self.categoria_nombre or ''


class Producto(models.Model):
    producto_id = models.AutoField(primary_key=True)
    producto_codigo_bar = models.CharField(max_length=255, null=True, blank=True)
    producto_nombre = models.CharField(max_length=255, null=True, blank=True)
    tipo_unidad = models.CharField(max_length=255, null=True, blank=True)
    producto_precio_venta = models.DecimalField(max_digits=38, decimal_places=2, null=True, blank=True)
    producto_marca = models.CharField(max_length=255, null=True, blank=True)
    producto_estado = models.CharField(max_length=255, null=True, blank=True)
    foto = models.CharField(max_length=255, null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, db_column='categoria_id')
    especificacion = models.CharField(max_length=255, null=True, blank=True)
    resumen = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'productos'

    def __str__(self):
        return self.producto_nombre or ''

    @property
    def precio_formateado(self):
        if self.producto_precio_venta:
            return f"${self.producto_precio_venta:,.0f}"
        return "$0"

    @property
    def get_categoria_nombre(self):
        if self.categoria:
            return self.categoria.categoria_nombre
        return "Sin categoría"


class Atributo(models.Model):
    atributo_id = models.AutoField(primary_key=True)
    atributo_nombre = models.CharField(max_length=255, null=True, blank=True)
    atributo_tipo = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'atributos'

    def __str__(self):
        return self.atributo_nombre or ''


class AtributoValor(models.Model):
    valor_id = models.AutoField(primary_key=True)
    atributo = models.ForeignKey(Atributo, on_delete=models.CASCADE, db_column='atributo_id')
    valor = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'atributo_valores'

    def __str__(self):
        return self.valor


class ProductoAtributo(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, primary_key=True, db_column='producto_id')
    atributo = models.ForeignKey(Atributo, on_delete=models.CASCADE, db_column='atributo_id')
    valor = models.ForeignKey(AtributoValor, on_delete=models.SET_NULL, null=True, blank=True, db_column='valor_id')
    valor_texto = models.CharField(max_length=255, null=True, blank=True)
    valor_numero = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'producto_atributos'
        unique_together = (('producto', 'atributo'),)


class Inventario(models.Model):
    inventario_id = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True, db_column='producto_id')
    inventario_stock_actual = models.IntegerField(null=True, blank=True)
    inventario_stock_minimo = models.IntegerField(null=True, blank=True)
    inventario_stock_maximo = models.IntegerField(null=True, blank=True)
    inventario_ubicacion = models.CharField(max_length=255, null=True, blank=True)
    inventario_fecha_actualizacion = models.DateField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    observaciones = models.CharField(max_length=255, null=True, blank=True)
    stock = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'inventario'

    def __str__(self):
        return f"Inv-{self.inventario_id}: {self.producto}"

    @property
    def stock_bajo(self):
        if self.inventario_stock_actual and self.inventario_stock_minimo:
            return self.inventario_stock_actual <= self.inventario_stock_minimo
        return False




class MetodoPago(models.Model):
    metodo_pago_id = models.IntegerField(primary_key=True)
    metodo_pago_nombre = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'metodos_pago'

    def __str__(self):
        return self.metodo_pago_nombre or ''


class Venta(models.Model):
    venta_codigo = models.AutoField(primary_key=True)
    venta_fecha = models.DateField(null=True, blank=True)
    venta_hora = models.TimeField(null=True, blank=True)
    venta_total = models.DecimalField(max_digits=38, decimal_places=2, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id', related_name='ventas_registradas')
    comprador = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='comprador_id', related_name='compras')
    cantidad = models.IntegerField(null=True, blank=True)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.SET_NULL, null=True, blank=True, db_column='metodo_pago_id')
    observaciones = models.CharField(max_length=255, null=True, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)
    total = models.FloatField(null=True, blank=True)
    numero_venta = models.IntegerField(null=True, blank=True, unique=True)

    class Meta:
        managed = False
        db_table = 'ventas'

    def __str__(self):
        return f"Venta #{self.venta_codigo}"

    @property
    def total_formateado(self):
        if self.venta_total:
            return f"${self.venta_total:,.0f}"
        return "$0"


class VentaDetalle(models.Model):
    venta_detalle_id = models.AutoField(primary_key=True)
    venta_detalle_cantidad = models.IntegerField(null=True, blank=True)
    venta_detalle_precio_venta = models.DecimalField(max_digits=38, decimal_places=2, null=True, blank=True)
    venta_detalle_iva = models.DecimalField(max_digits=38, decimal_places=2, null=True, blank=True)
    venta_detalle_descripcion = models.CharField(max_length=255, null=True, blank=True)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, null=True, blank=True, db_column='venta_codigo')
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True, blank=True, db_column='producto_id')
    subtotal = models.DecimalField(max_digits=38, decimal_places=2, null=True, blank=True)
    cantidad = models.IntegerField(null=True, blank=True)
    precio_unitario = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'venta_detalle'

    def __str__(self):
        return f"Detalle {self.venta_detalle_id}"


class MovimientoInventario(models.Model):
    movimiento_id = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True, db_column='producto_id')
    movimiento_tipo = models.CharField(max_length=255, null=True, blank=True)
    movimiento_cantidad = models.IntegerField(null=True, blank=True)
    movimiento_fecha = models.DateField(null=True, blank=True)
    movimiento_motivo = models.CharField(max_length=255, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column='user_id')
    venta = models.ForeignKey(Venta, on_delete=models.SET_NULL, null=True, blank=True, db_column='venta_id')
    movimiento_stock_anterior = models.IntegerField(null=True, blank=True)
    movimiento_stock_nuevo = models.IntegerField(null=True, blank=True)
    cantidad = models.IntegerField(null=True, blank=True)
    tipo_movimiento = models.CharField(max_length=255, null=True, blank=True)
    inventario = models.ForeignKey(Inventario, on_delete=models.SET_NULL, null=True, blank=True, db_column='inventario_id')

    class Meta:
        managed = False
        db_table = 'movimientos_inventario'

    def __str__(self):
        return f"Mov-{self.movimiento_id}: {self.movimiento_tipo}"
