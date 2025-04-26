from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def get_filter_count(context):
    count = 0
    # Degree filter
    if context.get('degree_filter'):
        count += 1
    # Stream filters
    count += len(context.get('stream_filters', []))
    # Percentage filters
    count += 1 if context.get('min_tenth') else 0
    count += 1 if context.get('min_twelfth') else 0
    count += 1 if context.get('min_degree') else 0
    # Gender filter
    count += 1 if context.get('gender_filter') else 0
    # Year filters
    count += 1 if context.get('min_yop') else 0
    count += 1 if context.get('max_yop') else 0
    return count


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

from django import template

register = template.Library()

@register.simple_tag
def query_transform(request, **kwargs):
    updated = request.GET.copy()
    for k, v in kwargs.items():
        if v is None:
            if k in updated:
                del updated[k]
        else:
            updated[k] = v
    return updated.urlencode()


@register.simple_tag(takes_context=True)
def modify_query(context, **kwargs):
    """
    Allows updating query parameters in templates.
    Usage: {% modify_query page=2 %}
    """
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()

from django import template
from urllib.parse import urlencode

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.dict()
    query.update(kwargs)
    return urlencode(query)

@register.filter
def to_str(value):
    return str(value)


@register.filter
def get_pie_color(index):
    colors = [
        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b',
        '#5a5c69', '#858796', '#dddfeb', '#f8f9fc', '#5a5c69'
    ]
    return colors[(index - 1) % len(colors)]

@register.filter
def get_pie_color_hover(index):
    colors = [
        '#2e59d9', '#17a673', '#2c9faf', '#dda20a', '#be2617',
        '#42444e', '#6b6d7d', '#c4c7d4', '#e5e8f4', '#42444e'
    ]
    return colors[(index - 1) % len(colors)]

@register.filter
def intdiv(value, arg):
    """Integer division filter"""
    try:
        return int(value) // int(arg)
    except (ValueError, ZeroDivisionError):
        return 0
    
@register.filter
def get_type_badge(type_str):
    type_str = (type_str or '').lower()
    badge_map = {
        'fsdi': 'badge-type-fsdi',
        'super100': 'badge-type-super100',
        'tuition': 'badge-type-tuition',
        'legend': 'badge-type-legend',
    }
    return badge_map.get(type_str, 'badge-type-default')

@register.filter
def replace(value, arg):
    """Replaces all instances of old with new in the string.
    Usage: {{ value|replace:"_,-" }} (replaces "_" with "-")
    """
    old, new = arg.split(',')
    return value.replace(old, new)