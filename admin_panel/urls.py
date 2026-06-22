from django.urls import path
from admin_panel import views
from admin_panel import reportes

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    # Productos
    path('productos/', views.productos_list, name='productos'),
    path('productos/crear/', views.producto_create, name='producto_create'),
    path('productos/<int:pk>/', views.producto_show, name='producto_show'),
    path('productos/<int:pk>/editar/', views.producto_edit, name='producto_edit'),
    path('productos/<int:pk>/eliminar/', views.producto_delete, name='producto_delete'),
    path('productos/color/nuevo/', views.color_nuevo, name='color_nuevo'),
    
    # Categorías
    path('categorias/', views.categorias_list, name='categorias'),
    path('categorias/crear/', views.categoria_create, name='categoria_create'),
    path('categorias/<int:pk>/editar/', views.categoria_edit, name='categoria_edit'),
    path('categorias/<int:pk>/eliminar/', views.categoria_delete, name='categoria_delete'),
    
    # Inventario
    path('inventario/', views.inventario_list, name='inventario'),
    path('inventario/<int:pk>/editar/', views.inventario_edit, name='inventario_edit'),
    
    # Movimientos
    path('movimientos/', views.movimientos_list, name='movimientos'),
    path('movimientos/crear/', views.movimiento_create, name='movimiento_create'),
    
    # Usuarios
    path('usuarios/', views.usuarios_list, name='usuarios'),
    path('usuarios/crear/', views.usuario_create, name='usuario_create'),
    path('usuarios/<int:pk>/editar/', views.usuario_edit, name='usuario_edit'),
    path('usuarios/<int:pk>/reset-password/', views.usuario_send_reset, name='usuario_send_reset'),
    path('usuarios/<int:pk>/eliminar/', views.usuario_delete, name='usuario_delete'),
    
    # Ventas
    path('ventas/', views.ventas_list, name='ventas'),
    path('ventas/nueva/', views.venta_create, name='venta_create'),
    path('ventas/<int:pk>/', views.venta_detalle_view, name='venta_detalle'),

    # ── Reportes ──────────────────────────────────────────────────
    path('reportes/', reportes.reportes_index, name='reportes_index'),
    path('reportes/productos/', reportes.reporte_productos_view, name='reporte_productos'),
    path('reportes/productos/pdf/', reportes.reporte_productos_pdf, name='reporte_productos_pdf'),
    path('reportes/ventas/', reportes.reporte_ventas_view, name='reporte_ventas'),
    path('reportes/ventas/pdf/', reportes.reporte_ventas_pdf, name='reporte_ventas_pdf'),
    path('reportes/inventario/', reportes.reporte_inventario_view, name='reporte_inventario'),
    path('reportes/inventario/pdf/', reportes.reporte_inventario_pdf, name='reporte_inventario_pdf'),
    path('reportes/usuarios/', reportes.reporte_usuarios_view, name='reporte_usuarios'),
    path('reportes/usuarios/pdf/', reportes.reporte_usuarios_pdf, name='reporte_usuarios_pdf'),
    path('reportes/clientes/', reportes.reporte_clientes_view, name='reporte_clientes'),
    path('reportes/clientes/pdf/', reportes.reporte_clientes_pdf, name='reporte_clientes_pdf'),
    path('reportes/vendedores/', reportes.reporte_vendedores_view, name='reporte_vendedores'),
    path('reportes/vendedores/pdf/', reportes.reporte_vendedores_pdf, name='reporte_vendedores_pdf'),

    # ── Carga Masiva ──────────────────────────────────────────────
    path('carga-masiva/', reportes.carga_masiva_view, name='carga_masiva'),
    path('carga-masiva/plantilla/csv/', reportes.descargar_plantilla_csv, name='plantilla_csv'),
    path('carga-masiva/plantilla/excel/', reportes.descargar_plantilla_excel, name='plantilla_excel'),
    path('carga-masiva/usuarios/', reportes.carga_masiva_usuarios_view, name='carga_masiva_usuarios'),
    path('carga-masiva/usuarios/plantilla/csv/', reportes.descargar_plantilla_usuarios_csv, name='plantilla_usuarios_csv'),
    path('carga-masiva/usuarios/plantilla/excel/', reportes.descargar_plantilla_usuarios_excel, name='plantilla_usuarios_excel'),
]
