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