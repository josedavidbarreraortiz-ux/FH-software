from accounts.models import Categoria


def categories_processor(request):
    """Make categories available in all templates for the navbar."""
    try:
        from django.core.cache import cache
        categorias = cache.get('nav_categorias')
        if categorias is None:
            categorias = list(Categoria.objects.filter(estado=1).order_by('categoria_id'))
            cache.set('nav_categorias', categorias, 300)
        return {'categorias_nav': categorias}
    except Exception:
        return {'categorias_nav': []}
