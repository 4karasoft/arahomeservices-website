from django.db import models


class InventoryItem(models.Model):
    """Inventory items from Telegram group. Format: TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD"""

    # Telegram metadata
    telegram_message_id = models.BigIntegerField(unique=True, db_index=True)
    chat_id = models.BigIntegerField(db_index=True)
    sender_username = models.CharField(max_length=100, blank=True)
    sender_name = models.CharField(max_length=200, blank=True)

    # Raw content
    raw_text = models.TextField()

    # Parsed fields: TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD
    mount_type = models.CharField(max_length=200, blank=True)
    size = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=200, blank=True)
    purchase_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'

    def __str__(self):
        return f"{self.mount_type or '?'} | {self.size or '?'} | {self.model or '?'} | ${self.purchase_cost_usd or '?'}"
