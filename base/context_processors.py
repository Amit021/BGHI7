from .models import DirectMessage


def unread_message_count(request):
    """Add unread message count to all templates."""
    if request.user.is_authenticated:
        count = DirectMessage.objects.filter(
            receiver=request.user,
            is_read=False
        ).count()
        return {'unread_message_count': count}
    return {'unread_message_count': 0}
