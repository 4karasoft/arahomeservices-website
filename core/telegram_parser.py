"""
Parses Telegram group messages for inventory.
Format: TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD
Example: Full motion, 400x400, xms999, 15
"""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional


@dataclass
class ParsedInventory:
    mount_type: str
    size: str
    model: str
    purchase_cost_usd: Optional[Decimal]


def parse_inventory_message(text: str) -> ParsedInventory:
    """
    Parse message in format: TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD
    Example: Full motion, 400x400, xms999, 15
    """
    if not text or not text.strip():
        return ParsedInventory('', '', '', None)

    # Split by comma, strip whitespace
    parts = [p.strip() for p in text.split(',')]

    mount_type = parts[0] if len(parts) > 0 else ''
    size = parts[1] if len(parts) > 1 else ''
    model = parts[2] if len(parts) > 2 else ''
    purchase_cost_usd = None

    if len(parts) > 3:
        cost_str = parts[3].strip()
        # Remove $ if present
        cost_str = re.sub(r'^\$', '', cost_str)
        try:
            purchase_cost_usd = Decimal(cost_str)
        except (InvalidOperation, ValueError):
            pass

    return ParsedInventory(
        mount_type=mount_type,
        size=size,
        model=model,
        purchase_cost_usd=purchase_cost_usd,
    )
