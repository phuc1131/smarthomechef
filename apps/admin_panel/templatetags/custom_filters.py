from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(obj, key):
    """Return value for mapping key or object attribute safely.

    Usage: {{ row|get_item:col }}
    Works for dicts, objects with attributes, and lists (by index).
    """
    if obj is None:
        return ''
    try:
        # dict-like access
        if isinstance(obj, dict):
            return obj.get(key, '')
        # list/tuple index access
        if isinstance(obj, (list, tuple)):
            try:
                idx = int(key)
            except Exception:
                return ''
            if 0 <= idx < len(obj):
                return obj[idx]
            return ''
        # try attribute access
        if hasattr(obj, key):
            return getattr(obj, key)
        # if obj has get method (QueryDict etc.)
        get = getattr(obj, 'get', None)
        if callable(get):
            return get(key, '')
    except Exception:
        return ''
    return ''
