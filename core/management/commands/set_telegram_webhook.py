"""
Set the Telegram webhook URL. Run once after deployment.

Usage:
    python manage.py set_telegram_webhook https://yourdomain.com/webhook/telegram/

Telegram requires HTTPS. For local testing, use ngrok:
    ngrok http 8000
    python manage.py set_telegram_webhook https://xxxx.ngrok.io/webhook/telegram/
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Register the Telegram webhook URL with Telegram'

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='Full webhook URL (e.g. https://arahomeservice.com/webhook/telegram/)',
        )

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            self.stderr.write(self.style.ERROR('TELEGRAM_BOT_TOKEN is not set in settings'))
            return

        url = options['url'].rstrip('/')
        if not url.startswith('https://'):
            self.stderr.write(self.style.ERROR('Webhook URL must use HTTPS'))
            return

        api_url = f'https://api.telegram.org/bot{token}/setWebhook'
        response = requests.post(api_url, json={'url': url}, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                self.stdout.write(self.style.SUCCESS(f'Webhook set successfully to {url}'))
            else:
                self.stderr.write(self.style.ERROR(f"Telegram API error: {data.get('description', 'Unknown')}"))
        else:
            self.stderr.write(self.style.ERROR(f'Request failed: {response.status_code} - {response.text}'))
