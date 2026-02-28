import json
import logging

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import AppointmentForm
from .models import InventoryItem
from .telegram_parser import parse_inventory_message

logger = logging.getLogger(__name__)


def home(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            # Get form data
            name = form.cleaned_data['name']
            phone = form.cleaned_data['phone']
            address = form.cleaned_data['address']
            appliance_type = form.cleaned_data['appliance_type']
            issue_description = form.cleaned_data['issue_description']
            
            # Construct message string with all lead details
            message_text = f"""New Appointment Request:

Name: {name}
Phone: {phone}
Address: {address}
Appliance Type: {appliance_type.replace('_', ' ').title()}
Issue Description: {issue_description}
"""
            
            # Telegram Notification
            try:
                # Check if Telegram settings are configured
                if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
                    print("Telegram settings not configured: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing")
                else:
                    # Create message with Markdown formatting
                    telegram_message_md = f"""🔧 *New Appointment Request*

*Name:* {name}
*Phone:* {phone}
*Address:* {address}
*Appliance:* {appliance_type.replace('_', ' ').title()}
*Issue:* {issue_description}
"""
                    
                    # Also create plain text version as fallback
                    telegram_message_plain = f"""🔧 New Appointment Request

Name: {name}
Phone: {phone}
Address: {address}
Appliance: {appliance_type.replace('_', ' ').title()}
Issue: {issue_description}
"""
                    
                    telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
                    
                    # Ensure chat_id is a string (Telegram API accepts both string and int)
                    chat_id = str(settings.TELEGRAM_CHAT_ID).strip()
                    
                    # Try sending with Markdown first
                    response = requests.post(
                        telegram_url,
                        json={
                            'chat_id': chat_id,
                            'text': telegram_message_md,
                            'parse_mode': 'Markdown'
                        },
                        timeout=10
                    )
                    
                    # Check the response from Telegram API
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get('ok'):
                            print("Telegram notification sent successfully")
                        else:
                            error_description = response_data.get('description', 'Unknown error')
                            error_code = response_data.get('error_code', '')
                            
                            # If Markdown parsing failed, try plain text
                            if error_code == 400 and 'parse' in error_description.lower():
                                print(f"Markdown parse error, retrying with plain text: {error_description}")
                                response = requests.post(
                                    telegram_url,
                                    json={
                                        'chat_id': chat_id,
                                        'text': telegram_message_plain
                                    },
                                    timeout=10
                                )
                                if response.status_code == 200 and response.json().get('ok'):
                                    print("Telegram notification sent successfully (plain text)")
                                else:
                                    print(f"Telegram API error (plain text retry): {response.json()}")
                            else:
                                print(f"Telegram API error: {error_description} (code: {error_code})")
                                print(f"Full response: {response_data}")
                    else:
                        print(f"Telegram API request failed with status code: {response.status_code}")
                        print(f"Response: {response.text}")
                        
            except requests.exceptions.RequestException as e:
                print(f"Telegram notification request failed: {e}")
            except Exception as e:
                # Log error but don't crash the site if Telegram fails
                print(f"Telegram notification failed with exception: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
            
            # Email Notification
            try:
                email_subject = f'New Appointment Request - {appliance_type.replace("_", " ").title()}'
                
                send_mail(
                    subject=email_subject,
                    message=message_text,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[settings.ADMIN_EMAIL],
                    fail_silently=False,
                )
            except Exception as e:
                # Log error but don't crash the site if email fails
                print(f"Email sending failed: {e}")
            
            # Redirect to thank you page
            return redirect('core:thank_you')
    else:
        form = AppointmentForm()
    
    return render(request, 'core/home.html', {'form': form})


def thank_you(request):
    return render(request, 'core/thank_you.html')


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """
    Receives updates from Telegram when messages are sent in the inventory group.
    Parses messages (TYPE_OF_MOUNT, SIZE, MODEL, PURCHASE_COST_IN_USD) and saves to database.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return JsonResponse({'ok': False, 'error': 'Bot not configured'}, status=500)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    # Telegram sends updates - can contain message, edited_message, etc.
    message = body.get('message') or body.get('edited_message')
    if not message:
        return JsonResponse({'ok': True})

    # Skip messages from bots
    from_user = message.get('from', {})
    if from_user.get('is_bot'):
        return JsonResponse({'ok': True})

    # Only process group/supergroup messages (not direct messages or channels)
    chat = message.get('chat', {})
    chat_type = chat.get('type')
    if chat_type not in ('group', 'supergroup'):
        return JsonResponse({'ok': True})

    # Only process messages from the configured inventory group
    inventory_group_id = settings.TELEGRAM_INVENTORY_GROUP_CHAT_ID
    if not inventory_group_id:
        return JsonResponse({'ok': True})  # Must be configured to process any messages
    try:
        expected_id = int(str(inventory_group_id).strip())
        if chat.get('id') != expected_id:
            return JsonResponse({'ok': True})
    except (ValueError, TypeError):
        logger.warning("TELEGRAM_INVENTORY_GROUP_CHAT_ID is invalid")
        return JsonResponse({'ok': True})

    chat_id = chat.get('id')
    text = message.get('text') or message.get('caption') or ''
    if not text or len(text.strip()) < 5:
        return JsonResponse({'ok': True})

    message_id = message.get('message_id')

    # Avoid duplicate processing
    if InventoryItem.objects.filter(telegram_message_id=message_id).exists():
        return JsonResponse({'ok': True})

    # Parse the message (format: mount_type, size, model, cost)
    parsed = parse_inventory_message(text)

    sender_name = ' '.join(filter(None, [
        from_user.get('first_name'),
        from_user.get('last_name'),
    ]))
    sender_username = from_user.get('username', '')

    try:
        InventoryItem.objects.create(
            telegram_message_id=message_id,
            chat_id=chat_id,
            sender_username=sender_username,
            sender_name=sender_name,
            raw_text=text,
            mount_type=parsed.mount_type,
            size=parsed.size,
            model=parsed.model,
            purchase_cost_usd=parsed.purchase_cost_usd,
        )
        logger.info(f"Saved inventory item {message_id} from chat {chat_id}")
    except Exception as e:
        logger.exception(f"Failed to save inventory item: {e}")
        return JsonResponse({'ok': False, 'error': str(e)}, status=200)

    return JsonResponse({'ok': True})


def inventory(request):
    """Display inventory from group messages."""
    items = InventoryItem.objects.all()
    total_cost = sum(
        (i.purchase_cost_usd or 0) for i in items
    )
    return render(request, 'core/inventory.html', {
        'items': items,
        'total_cost': total_cost,
    })

