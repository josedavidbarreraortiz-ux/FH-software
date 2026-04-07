from django.urls import path
from tienda import views

app_name = 'tienda'

urlpatterns = [
    path('', views.index, name='index'),
    path('productos/', views.catalogo, name='catalogo'),
    path('producto/<int:pk>/', views.producto_detalle, name='producto_detalle'),
    path('carrito/', views.carrito_view, name='carrito'),
    path('carrito/agregar/<int:pk>/', views.carrito_agregar, name='carrito_agregar'),
    path('carrito/eliminar/<int:pk>/', views.carrito_eliminar, name='carrito_eliminar'),
    path('carrito/actualizar/<int:pk>/', views.carrito_actualizar, name='carrito_actualizar'),
    path('checkout/', views.checkout, name='checkout'),
    path('pedidos/', views.pedidos, name='pedidos'),
    path('pedidos/<int:pk>/', views.pedido_detalle, name='pedido_detalle'),
    path('perfil/', views.perfil, name='perfil'),
]
