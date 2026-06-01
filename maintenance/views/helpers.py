"""Shared helpers and module globals for the views package."""
import logging
import csv
import io
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import (
    MaintenanceActivity, MaintenanceActivityType, 
    MaintenanceSchedule, MaintenanceChecklist,
    ActivityTypeCategory, ActivityTypeTemplate, MaintenanceReport,
    MaintenanceTimelineEntry
)
from equipment.models import Equipment
from core.models import EquipmentCategory, UserProfile
from equipment.models import Equipment, EquipmentDocument
from ..forms import (
    MaintenanceActivityForm, MaintenanceScheduleForm, 
    MaintenanceActivityTypeForm, EnhancedMaintenanceActivityTypeForm,
    ActivityTypeCategoryForm, ActivityTypeTemplateForm
)
from events.models import CalendarEvent
from ..models import (
    EquipmentCategorySchedule, GlobalSchedule, ScheduleOverride
)
from ..forms import (
    EquipmentCategoryScheduleForm, GlobalScheduleForm, ScheduleOverrideForm
)
from django.contrib.auth.models import User
from core.models import Location
from core.utils import get_all_descendant_location_ids  # noqa: F401

logger = logging.getLogger(__name__)



def analyze_report_content(content):
    """Analyze report content to extract structured data."""
    analyzed_data = {
        'issues': [],
        'parts_replaced': [],
        'measurements': [],
        'dates': [],
        'technicians': [],
        'work_hours': None,
    }
    import re
    # Convert to lowercase for case-insensitive matching
    content_lower = content.lower()

    # --- Enhanced: Extract issues from 'Issues found:' sections and bullet points ---
    # Find 'issues found:' or 'issues:' section
    issues_section = re.search(r'(issues found:|issues:)([\s\S]+?)(\n\s*\n|$)', content, re.IGNORECASE)
    if issues_section:
        issues_block = issues_section.group(2)
        # Extract bullet points or lines
        for line in issues_block.splitlines():
            line = line.strip('-•* ').strip()
            if not line:
                continue
            # Only consider lines that are not empty and not a section header
            severity = 'medium'  # Default severity
            lcline = line.lower()
            if any(word in lcline for word in ['critical', 'severe', 'emergency']):
                severity = 'critical'
            elif any(word in lcline for word in ['major', 'serious']):
                severity = 'high'
            elif any(word in lcline for word in ['minor', 'small']):
                severity = 'low'
            analyzed_data['issues'].append({
                'text': line,
                'severity': severity,
                'position': content.find(line)
            })

    # --- Existing: Extract issues (basic pattern matching) ---
    issue_patterns = [
        r'issue[s]?\s*:?  *([^.\n]+)',
        r'problem[s]?\s*:?  *([^.\n]+)',
        r'fault[s]?\s*:?  *([^.\n]+)',
        r'error[s]?\s*:?  *([^.\n]+)',
        r'failure[s]?\s*:?  *([^.\n]+)',
    ]
    for pattern in issue_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            issue_text = match.group(1).strip()
            severity = 'medium'  # Default severity
            if any(word in issue_text for word in ['critical', 'severe', 'emergency']):
                severity = 'critical'
            elif any(word in issue_text for word in ['major', 'serious']):
                severity = 'high'
            elif any(word in issue_text for word in ['minor', 'small']):
                severity = 'low'
            analyzed_data['issues'].append({
                'text': issue_text,
                'severity': severity,
                'position': match.start()
            })

    # --- Existing: Extract parts replaced ---
    parts_patterns = [
        r'replaced\s+([^.\n]+)',
        r'changed\s+([^.\n]+)',
        r'installed\s+new\s+([^.\n]+)',
        r'part[s]?\s*:?\s*([^.\n]+)',
    ]
    for pattern in parts_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            part_text = match.group(1).strip()
            analyzed_data['parts_replaced'].append({
                'part': part_text,
                'position': match.start()
            })

    # --- Existing: Extract measurements ---
    measurement_patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:psi|bar|pa|kpa|mpa|°c|°f|volts?|v|amps?|a|watts?|w|rpm|hz|khz|mhz)',
        r'temperature\s*:?\s*(\d+(?:\.\d+)?)\s*(?:°c|°f)',
        r'pressure\s*:?\s*(\d+(?:\.\d+)?)\s*(?:psi|bar|pa|kpa|mpa)',
    ]
    for pattern in measurement_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            value = match.group(1)
            unit = match.group(0).replace(value, '').strip()
            analyzed_data['measurements'].append({
                'value': float(value),
                'unit': unit,
                'position': match.start()
            })

    # --- Existing: Extract dates ---
    date_patterns = [
        r'\d{1,2}/\d{1,2}/\d{2,4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{1,2}-\d{1,2}-\d{2,4}',
    ]
    for pattern in date_patterns:
        matches = re.finditer(pattern, content)
        for match in matches:
            analyzed_data['dates'].append({
                'date': match.group(0),
                'position': match.start()
            })

    # --- Existing: Extract work hours ---
    hours_patterns = [
        r'(\d+(?:\.\d+)?)\s*hours?',
        r'(\d+(?:\.\d+)?)\s*hrs?',
        r'worked\s+(\d+(?:\.\d+)?)\s*hours?',
    ]
    for pattern in hours_patterns:
        match = re.search(pattern, content_lower)
        if match:
            analyzed_data['work_hours'] = float(match.group(1))
            break

    return analyzed_data


__all__ = ["analyze_report_content", "get_all_descendant_location_ids", "logger"]
