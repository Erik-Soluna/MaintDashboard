"""version views (split from the original monolithic views.py)."""
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


def version_view(request):
    """Display version information for debugging and verification."""
    try:
        import json
        import os
        from django.conf import settings
        
        # First try to read from version.json (most up-to-date)
        version_info = None
        version_json_path = os.path.join(settings.BASE_DIR, 'version.json')
        
        if os.path.exists(version_json_path):
            try:
                with open(version_json_path, 'r') as f:
                    version_info = json.load(f)
                logger.info(f"Loaded version info from version.json: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to read version.json: {str(e)}")
        
        # Fallback to environment variables
        if not version_info:
            version_info = {
                'commit_count': os.environ.get('GIT_COMMIT_COUNT', '0'),
                'commit_hash': os.environ.get('GIT_COMMIT_HASH', 'unknown'),
                'branch': os.environ.get('GIT_BRANCH', 'unknown'),
                'commit_date': os.environ.get('GIT_COMMIT_DATE', 'unknown'),
                'version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')}",
                'full_version': f"v{os.environ.get('GIT_COMMIT_HASH', 'unknown')} ({os.environ.get('GIT_BRANCH', 'unknown')}) - {os.environ.get('GIT_COMMIT_DATE', 'unknown')}"
            }
            logger.info(f"Loaded version info from environment variables: {version_info.get('version', 'unknown')}")
        
        # Final fallback to version.py module
        if not version_info or version_info.get('commit_hash') == 'unknown':
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
                version_info = version_module.get_git_version()
                logger.info(f"Loaded version info from version.py: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load version.py: {str(e)}")
                # Last resort fallback
                version_info = {
                    'commit_count': '0',
                    'commit_hash': 'unknown',
                    'branch': 'unknown',
                    'commit_date': 'unknown',
                    'version': 'v0.0.0',
                    'full_version': 'v0.0.0 (unknown) - Development'
                }
        
        return JsonResponse(version_info)
    except Exception as e:
        logger.error(f"Error getting version info: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get version information',
            'details': str(e)
        }, status=500)


def version_html_view(request):
    """Display version information in HTML format."""
    try:
        import json
        import os
        from django.conf import settings
        
        # First try to read from version.json (most up-to-date)
        version_info = None
        version_json_path = os.path.join(settings.BASE_DIR, 'version.json')
        
        if os.path.exists(version_json_path):
            try:
                with open(version_json_path, 'r') as f:
                    version_info = json.load(f)
                logger.info(f"Loaded version info from version.json: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to read version.json: {str(e)}")
        
        # Fallback to environment variables
        if not version_info:
            version_info = {
                'commit_count': os.environ.get('GIT_COMMIT_COUNT', '0'),
                'commit_hash': os.environ.get('GIT_COMMIT_HASH', 'unknown'),
                'branch': os.environ.get('GIT_BRANCH', 'unknown'),
                'commit_date': os.environ.get('GIT_COMMIT_DATE', 'unknown'),
                'version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')}",
                'full_version': f"v{os.environ.get('GIT_COMMIT_COUNT', '0')}.{os.environ.get('GIT_COMMIT_HASH', 'unknown')} ({os.environ.get('GIT_BRANCH', 'unknown')}) - {os.environ.get('GIT_COMMIT_DATE', 'unknown')}"
            }
            logger.info(f"Loaded version info from environment variables: {version_info.get('version', 'unknown')}")
        
        # Final fallback to version.py module
        if not version_info or version_info.get('commit_hash') == 'unknown':
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("version_module", settings.BASE_DIR / "version.py")
                version_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(version_module)
                version_info = version_module.get_git_version()
                logger.info(f"Loaded version info from version.py: {version_info.get('version', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load version.py: {str(e)}")
                # Last resort fallback
                version_info = {
                    'commit_count': '0',
                    'commit_hash': 'unknown',
                    'branch': 'unknown',
                    'commit_date': 'unknown',
                    'version': 'v0.0.0',
                    'full_version': 'v0.0.0 (unknown) - Development'
                }
        # Add deployment context
        deployment_info = {
            'debug_mode': settings.DEBUG,
            'timezone': str(settings.TIME_ZONE),
            'database_engine': settings.DATABASES['default']['ENGINE'] if 'default' in settings.DATABASES else 'unknown',
            'static_files_root': str(settings.STATIC_ROOT) if hasattr(settings, 'STATIC_ROOT') else 'not_set',
            'media_files_root': str(settings.MEDIA_ROOT) if hasattr(settings, 'MEDIA_ROOT') else 'not_set',
            'environment': os.environ.get('ENVIRONMENT', 'development'),
            'docker_container': os.environ.get('HOSTNAME', 'unknown'),
        }
        
        context = {
            'version_info': version_info,
            'deployment_info': deployment_info,
        }
        return render(request, 'core/version.html', context)
    except Exception as e:
        logger.error(f"Error getting version info for HTML view: {str(e)}")
        messages.error(request, f'Failed to get version information: {str(e)}')
        return redirect('core:dashboard')


@login_required
@user_passes_test(is_staff_or_superuser)
def version_form_view(request):
    """Display version form for manual version setting."""
    return render(request, 'core/version_form.html')


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def set_version_api(request):
    """API endpoint to set version information manually."""
    try:
        data = json.loads(request.body)
        commit_count = data.get('commit_count')
        commit_hash = data.get('commit_hash')
        branch = data.get('branch')
        commit_date = data.get('commit_date')
        
        # Validate required fields
        if not all([commit_count, commit_hash, branch, commit_date]):
            return JsonResponse({
                'success': False,
                'error': 'All fields are required: commit_count, commit_hash, branch, commit_date'
            }, status=400)
        
        # Import and call the Celery task
        from core.tasks import set_manual_version
        
        # Ensure commit_count is a valid integer
        try:
            commit_count_int = int(commit_count)
            if commit_count_int <= 0:
                commit_count_int = 1  # Fallback to 1 if invalid
        except (ValueError, TypeError):
            commit_count_int = 1  # Fallback to 1 if conversion fails
        
        # Validate commit_date format
        try:
            from datetime import datetime
            if isinstance(commit_date, str):
                # Try to parse the date to ensure it's valid
                date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                parsed_date = None
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(commit_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if not parsed_date:
                    return JsonResponse({
                        'success': False,
                        'error': f'Invalid date format: {commit_date}. Expected YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or YYYY/MM/DD'
                    }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Invalid date format: {commit_date}'
            }, status=400)
        
        result = set_manual_version.delay(commit_count_int, commit_hash, branch, commit_date)
        
        return JsonResponse({
            'success': True,
            'message': f'Version set to v{commit_count}.{commit_hash} ({branch}) - {commit_date}',
            'task_id': result.id,
            'version_info': {
                'version': f'v{commit_count_int}.{commit_hash}',
                'commit_count': commit_count_int,
                'commit_hash': commit_hash,
                'branch': branch,
                'commit_date': commit_date,
                'full_version': f'v{commit_count_int}.{commit_hash} ({branch}) - {commit_date}'
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error setting version: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error setting version: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def extract_version_from_url_api(request):
    """API endpoint to extract version information from a URL."""
    try:
        data = json.loads(request.body)
        url = data.get('url')
        
        if not url:
            return JsonResponse({
                'success': False,
                'error': 'URL is required'
            }, status=400)
        
        # Import and use the URL extractor
        from core.url_version_extractor import URLVersionExtractor
        
        extractor = URLVersionExtractor()
        result = extractor.extract_from_url(url)
        
        if 'error' in result:
            return JsonResponse({
                'success': False,
                'error': result['error'],
                'supported': result.get('supported', [])
            }, status=400)
        
        # Optionally auto-set the version
        auto_set = data.get('auto_set', False)
        if auto_set:
            # Import and call the Celery task
            from core.tasks import set_manual_version
            
            # Ensure commit_count is a valid integer
            try:
                commit_count_int = int(result['commit_count'])
                if commit_count_int <= 0:
                    commit_count_int = 1  # Fallback to 1 if invalid
            except (ValueError, TypeError):
                commit_count_int = 1  # Fallback to 1 if conversion fails
            
            # Validate commit_date format
            try:
                from datetime import datetime
                commit_date = result['commit_date']
                if isinstance(commit_date, str):
                    # Try to parse the date to ensure it's valid
                    date_formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
                    parsed_date = None
                    
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(commit_date, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not parsed_date:
                        return JsonResponse({
                            'success': False,
                            'error': f'Invalid date format from URL: {commit_date}. Expected YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY, or YYYY/MM/DD'
                        }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Invalid date format from URL: {result.get("commit_date", "unknown")}'
                }, status=400)
            
            task_result = set_manual_version.delay(
                commit_count_int, 
                result['commit_hash'], 
                result['branch'], 
                result['commit_date']
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Version extracted and set successfully',
                'task_id': task_result.id,
                'extracted_data': result
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Version extracted successfully',
                'extracted_data': result
            })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except ImportError:
        return JsonResponse({
            'success': False,
            'error': 'URL extraction not available. Missing dependencies.'
        }, status=500)
    except Exception as e:
        logger.error(f"Error extracting version from URL: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': f'Error extracting version from URL: {str(e)}'
        }, status=500)


__all__ = ["version_view", "version_html_view", "version_form_view", "set_version_api", "extract_version_from_url_api"]
