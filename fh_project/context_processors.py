from accounts.models import Categoria


def categories_processor(request):
    """Make categories available in all templates for the navbar."""
    try:
        categorias = Categoria.objects.filter(estado=1).order_by('categoria_id')
        return {'categorias_nav': categorias}
    except Exception:
        return {'categorias_nav': []}
