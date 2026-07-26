from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Notification(TimeStampedModel):
    LEVELS = [("info", "Info"), ("success", "Success"), ("warning", "Warning"), ("error", "Error")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True)
    level = models.CharField(max_length=16, choices=LEVELS, default="info")
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.title}"


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=160, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} by {self.actor}"


class SupportTicket(TimeStampedModel):
    STATUS = [("open", "Open"), ("pending", "Pending"), ("closed", "Closed")]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets"
    )
    subject = models.CharField(max_length=180)
    message = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="open")
    response = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.subject
