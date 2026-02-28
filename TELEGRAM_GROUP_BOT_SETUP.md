# Telegram Inventory Bot Setup

The bot receives messages from your Telegram inventory group and saves them to the database. View inventory at `/inventory/`.

## Message Format

```
TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD
```

Example:
```
Full motion, 400x400, xms999, 15
```

## What You Need

1. **TELEGRAM_BOT_TOKEN** – In your `.env` (same bot used for form notifications)
2. **TELEGRAM_INVENTORY_GROUP_CHAT_ID** – Your inventory group’s chat ID (required; add to `.env`)
3. **Public HTTPS URL** – Your site must be reachable over HTTPS

### Getting your group chat ID

Group chat IDs are negative numbers (e.g. `-1001234567890`). To find yours:

1. Add [@userinfobot](https://t.me/userinfobot) or [@getidsbot](https://t.me/getidsbot) to your group.
2. Send a message in the group; the bot will reply with the group’s ID.
3. Add it to `.env`: `TELEGRAM_INVENTORY_GROUP_CHAT_ID=-1001234567890`

The bot will only process messages from this group. Direct messages and other groups are ignored.

## Setup Steps

### 1. Run migrations

```bash
python manage.py migrate
```

### 2. Set the webhook

After deploying, run **once**:

```bash
python manage.py set_telegram_webhook https://arahomeservice.com/webhook/telegram/
```

### 3. Local testing with ngrok

```bash
ngrok http 8000
python manage.py set_telegram_webhook https://xxxx.ngrok-free.app/webhook/telegram/
```

## Where to View Inventory

- **Web page:** `https://yourdomain.com/inventory/`
- **Django Admin:** `https://yourdomain.com/admin/` → Inventory Items
