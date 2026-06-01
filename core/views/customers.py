"""customers views (split from the original monolithic views.py)."""
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


@login_required
@user_passes_test(is_staff_or_superuser)
def customers_settings(request):
    """Customer management view."""
    customers = Customer.objects.all().order_by('name')
    
    # Pagination
    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'customers': customers,
    }
    return render(request, 'core/customers_settings.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def add_customer(request):
    """Add new customer."""
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.name}" has been created successfully.')
            return redirect('core:customers_settings')
    else:
        form = CustomerForm()
    
    context = {
        'form': form,
        'title': 'Add Customer',
        'action': 'Add'
    }
    return render(request, 'core/customer_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
@require_http_methods(["POST"])
def add_customer_ajax(request):
    """Add new customer via AJAX for modal form."""
    try:
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.created_by = request.user
            customer.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Customer "{customer.name}" has been created successfully.',
                'customer': {
                    'id': customer.id,
                    'name': customer.name,
                    'code': customer.code
                }
            })
        else:
            # Return form errors
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors[0] if field_errors else 'Invalid input'
            
            return JsonResponse({
                'success': False,
                'error': 'Please correct the errors below.',
                'field_errors': errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error creating customer via AJAX: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while creating the customer.'
        }, status=500)


@login_required
@user_passes_test(is_staff_or_superuser)
def edit_customer(request, customer_id):
    """Edit existing customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.updated_by = request.user
            customer.save()
            messages.success(request, f'Customer "{customer.name}" has been updated successfully.')
            return redirect('core:customers_settings')
    else:
        form = CustomerForm(instance=customer)
    
    context = {
        'form': form,
        'customer': customer,
        'title': f'Edit Customer: {customer.name}',
        'action': 'Edit'
    }
    return render(request, 'core/customer_form.html', context)


@login_required
@user_passes_test(is_staff_or_superuser)
def delete_customer(request, customer_id):
    """Delete customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        # Check if customer has associated locations
        location_count = customer.locations.count()
        if location_count > 0:
            messages.error(
                request, 
                f'Cannot delete customer "{customer.name}" because it has {location_count} associated location(s). '
                'Please reassign or remove the locations first.'
            )
        else:
            customer_name = customer.name
            customer.delete()
            messages.success(request, f'Customer "{customer_name}" has been deleted successfully.')
        
        return redirect('core:customers_settings')
    
    # Get associated locations for confirmation
    associated_locations = customer.locations.all()
    
    context = {
        'customer': customer,
        'associated_locations': associated_locations,
        'location_count': associated_locations.count()
    }
    return render(request, 'core/delete_customer.html', context)


__all__ = ["customers_settings", "add_customer", "add_customer_ajax", "edit_customer", "delete_customer"]
