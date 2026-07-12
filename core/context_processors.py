from .models import Notification


def unread_notifications(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {"unread_notifications": count}
    return {"unread_notifications": 0}
