from django.contrib import admin
from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'mount_type', 'size', 'model', 'purchase_cost_usd', 'sender_name']
    list_filter = ['mount_type', 'created_at']
    search_fields = ['raw_text', 'mount_type', 'size', 'model', 'sender_username']
    readonly_fields = ['telegram_message_id', 'chat_id', 'sender_username', 'sender_name', 'raw_text', 'created_at']
