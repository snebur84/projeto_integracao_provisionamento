from django import template
from django.utils.html import format_html

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Usage in template:
      {{ form.field_name|add_class:"form-control" }}

    This returns the field rendered with the given CSS class appended to
    the widget's existing class attribute (does not mutate the form object).
    """
    # field is a BoundField
    try:
        existing = field.field.widget.attrs.get('class', '')
    except Exception:
        existing = ''

    # Merge classes (avoid duplicate spaces)
    classes = (existing + ' ' + css_class).strip()
    return field.as_widget(attrs={'class': classes})