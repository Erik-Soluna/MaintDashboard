#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maintenance_dashboard.settings')
django.setup()

from core.models import PlaywrightDebugLog

# Create test prompt
prompt = 'Create a new equipment item named "Test Equipment Sophie" and assign it to location "Sophie". The equipment should be a server with category "Servers".'

try:
    log_entry = PlaywrightDebugLog.objects.create(
        prompt=prompt,
        status='pending'
    )
    print(f'Test prompt created successfully with ID: {log_entry.id}')
    print(f'Prompt: {prompt}')
except Exception as e:
    print(f'Error creating test prompt: {e}') 