from .models import AuditLog, Notification


def notify(user, title, body="", level="info", link=""):
    return Notification.objects.create(
        user=user, title=title, body=body, level=level, link=link
    )


def log_action(actor, action, target="", metadata=None, request=None):
    ip = None
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        target=str(target),
        metadata=metadata or {},
        ip_address=ip,
    )
