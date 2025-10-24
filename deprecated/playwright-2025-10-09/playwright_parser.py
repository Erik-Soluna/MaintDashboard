"""
Natural language prompt parser for Playwright test orchestration.
Handles parsing user-friendly prompts into structured test actions.
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def parse_natural_language(prompt: str) -> List[Dict[str, Any]]:
    """
    Parse natural language prompt into structured test actions.
    
    Args:
        prompt: Natural language description of what to test
        
    Returns:
        List of structured actions to execute
    """
    prompt_lower = prompt.lower().strip()
    actions = []
    
    # Admin tool actions
    if any(keyword in prompt_lower for keyword in ['clear database', 'clear db', 'wipe database']):
        actions.append({
            'type': 'admin_clear_database',
            'keep_users': 'keep users' in prompt_lower,
            'keep_admin': 'keep admin' in prompt_lower,
            'dry_run': 'dry run' in prompt_lower or 'test' in prompt_lower,
            'description': 'Clear database with specified options'
        })
    
    if any(keyword in prompt_lower for keyword in ['populate demo', 'add demo data', 'create demo data']):
        actions.append({
            'type': 'admin_populate_demo',
            'reset_data': 'reset' in prompt_lower or 'clear first' in prompt_lower,
            'users_count': extract_number(prompt_lower, 'users', 10),
            'equipment_count': extract_number(prompt_lower, 'equipment', 50),
            'activities_count': extract_number(prompt_lower, 'activities', 100),
            'events_count': extract_number(prompt_lower, 'events', 75),
            'description': 'Populate demo data with specified quantities'
        })
    
    # Site and location actions
    if any(keyword in prompt_lower for keyword in ['create site', 'create a site', 'add site', 'generate pods']):
        actions.append({
            'type': 'create_site',
            'site_name': extract_site_name(prompt_lower),
            'pod_count': extract_number(prompt_lower, 'pods', 11),
            'mdcs_per_pod': extract_number(prompt_lower, 'mdcs', 2),
            'force': 'force' in prompt_lower,
            'description': 'Create site with PODs and MDCs'
        })
    
    # Equipment actions
    if any(keyword in prompt_lower for keyword in ['create equipment', 'add equipment', 'add device']):
        actions.append({
            'type': 'create_equipment',
            'equipment_name': extract_equipment_name(prompt_lower),
            'site_name': extract_site_name(prompt_lower),
            'category': extract_category(prompt_lower),
            'description': 'Create equipment in specified location'
        })
    
    # User and role actions
    if any(keyword in prompt_lower for keyword in ['create user', 'add user', 'register user']):
        actions.append({
            'type': 'create_user',
            'username': extract_username(prompt_lower),
            'role': extract_role(prompt_lower),
            'description': 'Create user with specified role'
        })
    
    # RBAC testing actions
    if any(keyword in prompt_lower for keyword in ['test rbac', 'test permissions', 'test access']):
        actions.append({
            'type': 'test_rbac',
            'user_role': extract_role(prompt_lower),
            'action': extract_action(prompt_lower),
            'expected_result': 'denied' if 'deny' in prompt_lower else 'allowed',
            'description': 'Test RBAC permissions for specific user and action'
        })
    
    # General testing actions
    if any(keyword in prompt_lower for keyword in ['test page', 'check page', 'verify page']):
        actions.append({
            'type': 'test_page',
            'page_name': extract_page_name(prompt_lower),
            'expected_elements': extract_expected_elements(prompt_lower),
            'description': 'Test specific page functionality'
        })
    
    # If no specific actions found, create a general test
    if not actions:
        actions.append({
            'type': 'general_test',
            'description': f'General test for prompt: {prompt}',
            'prompt': prompt
        })
    
    logger.info(f"Parsed prompt '{prompt}' into {len(actions)} actions: {actions}")
    return actions


def extract_number(text: str, keyword: str, default: int) -> int:
    """Extract a number associated with a keyword from text."""
    patterns = [
        rf'{keyword}[:\s]*(\d+)',
        rf'(\d+)\s*{keyword}',
        rf'{keyword}\s*count[:\s]*(\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    
    return default


def extract_site_name(text: str) -> str:
    """Extract site name from text."""
    patterns = [
        r'create\s+a\s+site\s+called\s+([a-zA-Z0-9\s]+?)\s+with',  # NEW: matches 'create a site called Test Site with ...'
        r'site[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|with|and)',
        r'create\s+([a-zA-Z0-9\s]+?)\s+site',
        r'add\s+([a-zA-Z0-9\s]+?)\s+site',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return 'Test Site'


def extract_equipment_name(text: str) -> str:
    """Extract equipment name from text."""
    patterns = [
        r'equipment[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|in|at)',
        r'device[:\s]*([a-zA-Z0-9\s]+?)(?:\s|$|in|at)',
        r'create\s+([a-zA-Z0-9\s]+?)\s+equipment',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return 'Test Equipment'


def extract_category(text: str) -> str:
    """Extract equipment category from text."""
    categories = ['transformer', 'switchgear', 'relay', 'breaker', 'controller', 'panel']
    
    for category in categories:
        if category in text:
            return category.title()
    
    return 'Transformers'


def extract_username(text: str) -> str:
    """Extract username from text."""
    patterns = [
        r'user[:\s]*([a-zA-Z0-9_]+?)(?:\s|$|with|and)',
        r'username[:\s]*([a-zA-Z0-9_]+?)(?:\s|$|with|and)',
        r'create\s+([a-zA-Z0-9_]+?)\s+user',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return 'test_user'


def extract_role(text: str) -> str:
    """Extract user role from text."""
    roles = ['admin', 'administrator', 'manager', 'technician', 'viewer', 'operator']
    
    for role in roles:
        if role in text:
            return role.title()
    
    return 'Technician'


def extract_action(text: str) -> str:
    """Extract action to test from text."""
    actions = ['clear database', 'populate demo', 'create site', 'create equipment', 'access settings']
    
    for action in actions:
        if action in text:
            return action
    
    return 'access settings'


def extract_page_name(text: str) -> str:
    """Extract page name from text."""
    pages = ['dashboard', 'settings', 'equipment', 'maintenance', 'events', 'users', 'locations']
    
    for page in pages:
        if page in text:
            return page.title()
    
    return 'Dashboard'


def extract_expected_elements(text: str) -> List[str]:
    """Extract expected elements from text."""
    elements = []
    common_elements = ['button', 'form', 'table', 'link', 'modal', 'alert', 'chart']
    
    for element in common_elements:
        if element in text:
            elements.append(element)
    
    return elements 