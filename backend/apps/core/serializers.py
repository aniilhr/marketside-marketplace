from rest_framework import serializers

from .models import AuditLog, Notification, SupportTicket


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "level", "link", "is_read", "created_at"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", default="", read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor_email", "action", "target", "metadata", "created_at"]


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = ["id", "subject", "message", "status", "response", "created_at"]
        read_only_fields = ["status", "response", "created_at"]
