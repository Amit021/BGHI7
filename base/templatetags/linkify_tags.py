import re
from django import template
from django.utils.safestring import mark_safe
from django.utils.html import escape

register = template.Library()


@register.filter(name='linkify')
def linkify(text):
    """
    Convert URLs in text to clickable links.
    Only used for Study Materials comments.
    """
    if not text:
        return text
    
    # Escape HTML first to prevent XSS
    text = escape(text)
    
    # URL pattern
    url_pattern = re.compile(
        r'(https?://[^\s<>"\']+)',
        re.IGNORECASE
    )
    
    def replace_url(match):
        url = match.group(1)
        # Truncate display URL if too long
        display_url = url if len(url) <= 50 else url[:47] + '...'
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="color: var(--color-main); text-decoration: underline;">{display_url}</a>'
    
    result = url_pattern.sub(replace_url, text)
    return mark_safe(result)
