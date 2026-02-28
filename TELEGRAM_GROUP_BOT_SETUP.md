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
2. **Public HTTPS URL** – Your site must be reachable over HTTPS

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
