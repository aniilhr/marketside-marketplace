from django.contrib import admin

from .models import AuditLog, Notification, SupportTicket

admin.site.register([Notification, AuditLog, SupportTicket])
