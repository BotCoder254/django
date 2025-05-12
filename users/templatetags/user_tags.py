from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    """
    Add a CSS class to the field's widget
    """
    if hasattr(field, 'field') and hasattr(field.field, 'widget'):
        attrs = field.field.widget.attrs
        original_class = attrs.get('class', '')
        if original_class:
            attrs['class'] = f"{original_class} {css_class}"
        else:
            attrs['class'] = css_class
    return field

@register.filter
def abs(value):
    """
    Return the absolute value of a number
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value 