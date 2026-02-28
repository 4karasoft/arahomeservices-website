import json
import re
import logging

import requests
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg, Count, Max
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import AppointmentForm
from .models import InventoryItem
from .telegram_parser import parse_inventory_message

logger = logging.getLogger(__name__)


def _size_sort_key(size_str):
    """
    Parse size string like "400x400" or "200x300" to a tuple for sorting (smallest first).
    Unparseable sizes return (9999, 9999) so they sort last.
    """
    if not size_str or not str(size_str).strip():
        return (9999, 9999)
    s = str(size_str).strip().lower()
    match = re.match(r"^(\d+)\s*[x×]\s*(\d+)$", s)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    # Single number?
    match = re.match(r"^(\d+)$", s)
    if match:
        n = int(match.group(1))
        return (n, n)
    return (9999, 9999)


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

    # Log that we received an update (helps debug: is Telegram calling the webhook?)
    update_id = body.get('update_id', '?')
    logger.info(f"[Telegram webhook] Received update_id={update_id}")

    # Telegram sends updates - can contain message, edited_message, etc.
    message = body.get('message') or body.get('edited_message')
    if not message:
        logger.info("[Telegram webhook] Ignored: no message in update")
        return JsonResponse({'ok': True})

    # Skip messages from bots
    from_user = message.get('from', {})
    if from_user.get('is_bot'):
        logger.info("[Telegram webhook] Ignored: message from bot")
        return JsonResponse({'ok': True})

    # Only process group/supergroup messages (not direct messages or channels)
    chat = message.get('chat', {})
    chat_type = chat.get('type')
    chat_id = chat.get('id')
    if chat_type not in ('group', 'supergroup'):
        logger.info(f"[Telegram webhook] Ignored: chat_type={chat_type!r} (need group/supergroup), chat_id={chat_id}")
        return JsonResponse({'ok': True})

    # Only process messages from the configured inventory group
    raw_group_id = settings.TELEGRAM_INVENTORY_GROUP_CHAT_ID
    if not raw_group_id:
        logger.info("[Telegram webhook] Ignored: TELEGRAM_INVENTORY_GROUP_CHAT_ID not set")
        return JsonResponse({'ok': True})
    # Normalize: strip whitespace and remove surrounding quotes (common in env configs)
    inventory_group_id = str(raw_group_id).strip().strip('"\'')
    try:
        expected_id = int(inventory_group_id)
        if chat_id != expected_id:
            logger.info(f"[Telegram webhook] Ignored: chat_id {chat_id} != expected {expected_id}")
            return JsonResponse({'ok': True})
    except (ValueError, TypeError):
        logger.warning(
            "[Telegram webhook] TELEGRAM_INVENTORY_GROUP_CHAT_ID is invalid (must be a number, e.g. -1001234567890). "
            "Got: %s", repr(raw_group_id)[:50]
        )
        return JsonResponse({'ok': True})

    text = message.get('text') or message.get('caption') or ''
    if not text or len(text.strip()) < 5:
        logger.info(f"[Telegram webhook] Ignored: message too short (len={len(text.strip())})")
        return JsonResponse({'ok': True})

    message_id = message.get('message_id')

    # Avoid duplicate processing
    if InventoryItem.objects.filter(telegram_message_id=message_id).exists():
        logger.info(f"[Telegram webhook] Ignored: duplicate message_id={message_id}")
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
    """Display inventory grouped by model + size, with count and average price."""
    items = InventoryItem.objects.all()
    total_cost = sum(
        (float(i.purchase_cost_usd) if i.purchase_cost_usd is not None else 0) for i in items
    )
    groups_qs = (
        InventoryItem.objects.values("model", "size")
        .annotate(
            count=Count("id"),
            avg_price=Avg("purchase_cost_usd"),
            mount_type=Max("mount_type"),
        )
        .order_by("size", "model")
    )
    groups = []
    for row in groups_qs:
        model = (row["model"] or "").strip() or "—"
        size = (row["size"] or "").strip() or "—"
        avg_price = row["avg_price"]
        count = row["count"]
        mount_type = (row["mount_type"] or "").strip() or "—"
        sk = _size_sort_key(size)
        groups.append({
            "model": model,
            "size": size,
            "count": count,
            "avg_price": float(avg_price) if avg_price is not None else None,
            "mount_type": mount_type,
            "size_sort_key": sk,
            "size_a": sk[0],
            "size_b": sk[1],
        })
    groups.sort(key=lambda g: g["size_sort_key"])
    return render(request, "core/inventory.html", {
        "groups": groups,
        "total_cost": total_cost,
    })

