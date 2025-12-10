from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
import requests

from .forms import AppointmentForm


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

