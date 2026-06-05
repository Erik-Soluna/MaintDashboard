"""webhooks views (split from the original monolithic views.py)."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from equipment.models import Equipment
from maintenance.models import MaintenanceActivity
from events.models import CalendarEvent
from core.models import Location, EquipmentCategory, Role, Permission, UserProfile, Customer, BrandingSettings, DashboardSettings, CSSCustomization
from core.forms import LocationForm, EquipmentCategoryForm, CustomerForm, UserForm, BrandingSettingsForm, BrandingBasicForm, BrandingNavigationForm, BrandingAppearanceForm, CSSCustomizationForm, CSSPreviewForm, DashboardSettingsForm
from django.utils import timezone
from django.db.models import Q, Count
from datetime import datetime, timedelta, date
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.core.management import call_command
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from io import StringIO
import json
import csv
import re
import time
import psutil
import logging
import shutil
import redis
from django_celery_beat.models import PeriodicTask
import requests
from django.test import RequestFactory
from django.contrib.admin.views.decorators import staff_member_required
import hmac
import hashlib
import os
import shutil
import redis
from django_celery_beat.models import PeriodicTask
from django.utils import timezone
from .helpers import *  # noqa: F401,F403 (shared helpers + globals)


def get_deployment_status(config):
    """Collect as much deployment detail as possible automatically: the running
    app version, the parsed Portainer endpoint/stack-webhook id, config timestamps,
    and — when Portainer API credentials are configured — live stack details
    (name, status, git ref/commit, last update). All best-effort."""
    import json as _json
    from urllib.parse import urlparse

    status = {'version': {}, 'portainer': {}, 'stack': None, 'errors': []}

    # Running app version (from version.json — always available)
    try:
        vf = settings.BASE_DIR / 'version.json'
        if vf.exists():
            with open(vf) as f:
                vi = _json.load(f)
            status['version'] = {
                'version': vi.get('version'), 'full': vi.get('full_version'),
                'commit': vi.get('commit_hash'), 'branch': vi.get('branch'),
                'date': vi.get('commit_date'), 'count': vi.get('commit_count'),
            }
    except Exception as e:
        status['errors'].append(f'version: {e}')

    url = (config.portainer_url or '').strip()
    if url:
        p = urlparse(url)
        base = f'{p.scheme}://{p.netloc}' if p.scheme else ''
        wid = url.rstrip('/').split('/')[-1].split('?')[0]
        status['portainer'] = {
            'base': base,
            'webhook_id': wid,
            'image_tag': config.image_tag,
            'polling': config.get_polling_frequency_display() if hasattr(config, 'get_polling_frequency_display') else config.polling_frequency,
            'stack_name': config.stack_name or None,
            'last_commit': (config.last_commit_hash or '')[:8] or None,
            'last_commit_date': config.last_commit_date,
            'last_check': config.last_check_date,
            'has_api_creds': bool(config.portainer_user and config.portainer_password),
        }
        # Live Portainer stack details (only if API credentials are configured)
        if config.portainer_user and config.portainer_password and base:
            try:
                jwt = requests.post(f'{base}/api/auth',
                                    json={'username': config.portainer_user, 'password': config.portainer_password},
                                    timeout=10).json().get('jwt')
                if jwt:
                    stacks = requests.get(f'{base}/api/stacks',
                                          headers={'Authorization': f'Bearer {jwt}'}, timeout=10).json()
                    match = None
                    for s in (stacks or []):
                        au = s.get('AutoUpdate') or {}
                        if au.get('Webhook') and au.get('Webhook') in url:
                            match = s
                            break
                        if config.stack_name and s.get('Name') == config.stack_name:
                            match = s
                    if match:
                        git = match.get('GitConfig') or {}
                        status['stack'] = {
                            'id': match.get('Id'),
                            'name': match.get('Name'),
                            'status': 'active' if match.get('Status') == 1 else 'inactive',
                            'git_url': git.get('URL'),
                            'git_ref': (git.get('ReferenceName') or '').replace('refs/heads/', '') or None,
                            'git_commit': (git.get('ConfigHash') or '')[:8] or None,
                            'update_date': match.get('UpdateDate'),
                        }
            except Exception as e:
                status['errors'].append(f'portainer api: {e}')
    return status


@login_required
@user_passes_test(is_staff_or_superuser)
def webhook_settings(request):
    """Webhook management settings page."""
    from core.models import PortainerConfig

    # Add comprehensive debugging
    logger.info(f"=== WEBHOOK SETTINGS DEBUG ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request POST data: {dict(request.POST)}")
    
    if request.method == 'POST':
        action = request.POST.get('action')
        logger.info(f"Action received: {action}")
        
        if action == 'save_config':
            logger.info("=== SAVE CONFIG ACTION STARTED ===")
            # Save configuration to database
            try:
                config = PortainerConfig.get_config()
                logger.info(f"Retrieved config object: {config}")
                logger.info(f"Current config - URL: '{config.portainer_url}', Stack: '{config.stack_name}'")
                
                # Handle sensitive fields - only update if user provides new values
                portainer_user = request.POST.get('portainer_user', '')
                portainer_password = request.POST.get('portainer_password', '')
                webhook_secret = request.POST.get('webhook_secret', '')
                portainer_url = request.POST.get('portainer_url', '')
                stack_name = request.POST.get('stack_name', '')
                image_tag = request.POST.get('image_tag', 'latest')
                polling_frequency = request.POST.get('polling_frequency', 'disabled')
                
                logger.info(f"Form data received:")
                logger.info(f"  URL: '{portainer_url}'")
                logger.info(f"  Stack: '{stack_name}'")
                logger.info(f"  Image Tag: '{image_tag}'")
                logger.info(f"  Polling Frequency: '{polling_frequency}'")
                logger.info(f"  User: '{portainer_user[:3]}***' if exists")
                logger.info(f"  Password: '***' if exists")
                logger.info(f"  Secret: '{webhook_secret[:4]}***' if exists")
                
                # If user enters masked values (like "***"), keep current values
                if portainer_user and not portainer_user.startswith('***'):
                    config.portainer_user = portainer_user
                    logger.info("Updated portainer_user")
                elif not portainer_user:
                    config.portainer_user = ''  # Allow clearing
                    logger.info("Cleared portainer_user")
                    
                if portainer_password and not portainer_password.startswith('*'):
                    config.portainer_password = portainer_password
                    logger.info("Updated portainer_password")
                elif not portainer_password:
                    config.portainer_password = ''  # Allow clearing
                    logger.info("Cleared portainer_password")
                    
                if webhook_secret and not webhook_secret.startswith('****'):
                    config.webhook_secret = webhook_secret
                    logger.info("Updated webhook_secret")
                elif not webhook_secret:
                    config.webhook_secret = ''  # Allow clearing
                    logger.info("Cleared webhook_secret")
                
                # Update non-sensitive fields
                config.portainer_url = portainer_url
                config.stack_name = stack_name
                config.image_tag = image_tag
                config.polling_frequency = polling_frequency
                logger.info(f"Updated URL to: '{config.portainer_url}'")
                logger.info(f"Updated Stack to: '{config.stack_name}'")
                logger.info(f"Updated Image Tag to: '{config.image_tag}'")
                logger.info(f"Updated Polling Frequency to: '{config.polling_frequency}'")
                
                # Validate required fields
                if not config.portainer_url:
                    logger.error("Validation failed: Portainer URL is required")
                    error_message = 'Portainer URL is required. Please enter a valid URL.'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': error_message})
                    else:
                        messages.error(request, error_message)
                        return redirect('core:webhook_settings')
                
                # Stack name is optional, so no validation needed
                
                logger.info("Validation passed, attempting to save...")
                
                # Save to database
                config.save()
                logger.info(f"=== SAVE SUCCESSFUL ===")
                logger.info(f"Saved config - URL: '{config.portainer_url}', Stack: '{config.stack_name}'")
                
                # Show what was saved
                saved_items = []
                if config.portainer_url:
                    saved_items.append(f"Portainer URL: {config.portainer_url}")
                if config.stack_name:
                    saved_items.append(f"Stack Name: {config.stack_name}")
                if config.image_tag:
                    saved_items.append(f"Image Tag: {config.image_tag}")
                if config.polling_frequency:
                    saved_items.append(f"Polling Frequency: {config.get_polling_frequency_display()}")
                if config.portainer_user:
                    saved_items.append(f"Username: {config.portainer_user[:3]}***")
                if config.portainer_password:
                    saved_items.append("Password: ********")
                if config.webhook_secret:
                    saved_items.append(f"Secret: {config.webhook_secret[:4]}****")
                
                success_message = f'Configuration saved successfully! Saved: {", ".join(saved_items)}'
                logger.info(f"Success message: {success_message}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'success', 'message': success_message})
                else:
                    messages.success(request, success_message)
                    
            except Exception as e:
                logger.error(f"=== SAVE ERROR ===")
                logger.error(f"Error saving webhook config: {str(e)}")
                logger.error(f"Exception type: {type(e).__name__}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                error_message = f'Error saving configuration: {str(e)}'
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_message})
                else:
                    messages.error(request, error_message)
                
        elif action == 'test_webhook':
            logger.info("=== TEST WEBHOOK ACTION ===")
            # Test the webhook configuration
            try:
                config = PortainerConfig.get_config()
                if not config.portainer_url:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': 'Cannot test webhook: Webhook URL not configured. Please save your configuration first.'})
                    else:
                        messages.error(request, 'Cannot test webhook: Webhook URL not configured. Please save your configuration first.')
                        return redirect('core:webhook_settings')
                
                result = test_portainer_connection()
                if 'reachable' in result.lower() or 'successful' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'success', 'message': f'✅ Webhook test successful: {result}'})
                    else:
                        messages.success(request, f'✅ Webhook test successful: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': f'❌ Webhook test failed: {result}'})
                    else:
                        messages.error(request, f'❌ Webhook test failed: {result}')
                else:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'warning', 'message': f'⚠️ Webhook test result: {result}'})
                    else:
                        messages.warning(request, f'⚠️ Webhook test result: {result}')
            except Exception as e:
                logger.error(f"Error testing webhook: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'❌ Webhook test error: {str(e)}'})
                else:
                    messages.error(request, f'❌ Webhook test error: {str(e)}')
                
        elif action == 'update_stack':
            logger.info("=== UPDATE STACK ACTION ===")
            # Manually trigger stack update via webhook
            try:
                config = PortainerConfig.get_config()
                if not config.portainer_url:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': 'Cannot update stack: Webhook URL not configured. Please save your configuration first.'})
                    else:
                        messages.error(request, 'Cannot update stack: Webhook URL not configured. Please save your configuration first.')
                        return redirect('core:webhook_settings')
                
                result = trigger_portainer_stack_update()
                if 'successfully' in result.lower() or 'triggered' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'success', 'message': f'✅ Stack update triggered: {result}'})
                    else:
                        messages.success(request, f'✅ Stack update triggered: {result}')
                elif 'failed' in result.lower() or 'error' in result.lower():
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'error', 'message': f'❌ Stack update failed: {result}'})
                    else:
                        messages.error(request, f'❌ Stack update failed: {result}')
                else:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'status': 'warning', 'message': f'⚠️ Stack update result: {result}'})
                    else:
                        messages.warning(request, f'⚠️ Stack update result: {result}')
            except Exception as e:
                logger.error(f"Error updating stack: {str(e)}")
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': f'❌ Stack update error: {str(e)}'})
                else:
                    messages.error(request, f'❌ Stack update error: {str(e)}')
        
        # Only redirect for non-AJAX requests
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return redirect('core:webhook_settings')
        else:
            return JsonResponse({'status': 'success', 'message': 'Action completed'})
    
    # Get configuration from database
    config = PortainerConfig.get_config()
    logger.info(f"=== LOADING CONFIG FOR DISPLAY ===")
    logger.info(f"Config object: {config}")
    logger.info(f"Config URL: '{config.portainer_url}'")
    logger.info(f"Config Stack: '{config.stack_name}'")
    
    # Mask sensitive data for display
    portainer_user = config.portainer_user
    portainer_password = config.portainer_password
    webhook_secret = config.webhook_secret
    
    # Show masked values if they exist
    if portainer_user:
        portainer_user = portainer_user[:3] + '*' * (len(portainer_user) - 3) if len(portainer_user) > 3 else '***'
    if portainer_password:
        portainer_password = '*' * 8  # Show 8 asterisks for password
    if webhook_secret:
        webhook_secret = webhook_secret[:4] + '*' * (len(webhook_secret) - 4) if len(webhook_secret) > 4 else '****'
    
    # Debug logging
    logger.info(f"Portainer config loaded - URL: {config.portainer_url}, Stack: {config.stack_name}, User: {config.portainer_user[:3] if config.portainer_user else 'None'}***")
    
    context = {
        'portainer_url': config.portainer_url,
        'portainer_user': portainer_user,
        'portainer_password': portainer_password,
        'stack_name': config.stack_name,
        'image_tag': config.image_tag,
        'polling_frequency': config.polling_frequency,
        'polling_choices': config.POLLING_CHOICES,
        'webhook_secret': webhook_secret,
        'deployment_status': get_deployment_status(config),
        'debug_info': {
            'url_exists': bool(config.portainer_url),
            'stack_exists': bool(config.stack_name),
            'tag_exists': bool(config.image_tag),
            'polling_exists': bool(config.polling_frequency),
            'user_exists': bool(config.portainer_user),
            'password_exists': bool(config.portainer_password),
            'secret_exists': bool(config.webhook_secret),
            'last_commit_hash': config.last_commit_hash[:8] if config.last_commit_hash else None,
            'last_update_date': config.last_commit_date.strftime('%Y-%m-%d %H:%M:%S') if config.last_commit_date else None,
            'last_check_date': config.last_check_date.strftime('%Y-%m-%d %H:%M:%S') if config.last_check_date else None,
        }
    }
    
    logger.info(f"=== RENDERING TEMPLATE ===")
    logger.info(f"Context debug_info: {context['debug_info']}")
    
    return render(request, 'core/webhook_settings.html', context)


__all__ = ["webhook_settings"]
