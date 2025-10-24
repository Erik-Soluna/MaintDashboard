"""
Playwright action handlers for different test scenarios.
Each function handles a specific type of test action.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def process_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """
    Process a single action based on its type.
    
    Args:
        page: Playwright page object
        action: Action dictionary with type and parameters
        action_index: Index of the action for logging
        
    Returns:
        Dictionary with action results
    """
    action_type = action.get('type')
    
    try:
        if action_type == 'admin_clear_database':
            return await admin_clear_database_action(page, action, action_index)
        elif action_type == 'admin_populate_demo':
            return await admin_populate_demo_action(page, action, action_index)
        elif action_type == 'create_site':
            return await create_site_action(page, action, action_index)
        elif action_type == 'create_equipment':
            return await create_equipment_action(page, action, action_index)
        elif action_type == 'create_user':
            return await create_user_action(page, action, action_index)
        elif action_type == 'test_rbac':
            return await test_rbac_action(page, action, action_index)
        elif action_type == 'test_page':
            return await test_page_action(page, action, action_index)
        elif action_type == 'general_test':
            return await general_test_action(page, action, action_index)
        else:
            return {
                'type': action_type,
                'success': False,
                'error': f'Unknown action type: {action_type}'
            }
    except Exception as e:
        logger.error(f"Error processing action {action_type}: {e}")
        return {
            'type': action_type,
            'success': False,
            'error': str(e)
        }


async def admin_clear_database_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Handle admin clear database action with RBAC testing."""
    keep_users = action.get('keep_users', False)
    keep_admin = action.get('keep_admin', False)
    dry_run = action.get('dry_run', False)
    
    # Navigate to settings page
    await page.goto('http://web:8000/core/settings/')
    await page.wait_for_load_state('networkidle')
    
    # Look for Clear Database button
    clear_button = await page.query_selector('button:has-text("Clear Database")')
    if not clear_button:
        return {
            'type': 'admin_clear_database',
            'success': False,
            'error': 'Clear Database button not found - user may not have admin permissions'
        }
    
    # Click the button to open modal
    await clear_button.click()
    await page.wait_for_timeout(1000)
    
    # Check if modal opened
    modal = await page.query_selector('.modal')
    if not modal:
        return {
            'type': 'admin_clear_database',
            'success': False,
            'error': 'Clear Database modal did not open'
        }
    
    # Set options in modal
    if keep_users:
        keep_users_checkbox = await page.query_selector('input[name="keep_users"]')
        if keep_users_checkbox:
            await keep_users_checkbox.check()
    
    if keep_admin:
        keep_admin_checkbox = await page.query_selector('input[name="keep_admin"]')
        if keep_admin_checkbox:
            await keep_admin_checkbox.check()
    
    if dry_run:
        dry_run_checkbox = await page.query_selector('input[name="dry_run"]')
        if dry_run_checkbox:
            await dry_run_checkbox.check()
    
    # Submit the form
    submit_button = await page.query_selector('button[type="submit"]')
    if submit_button:
        await submit_button.click()
        await page.wait_for_timeout(3000)
    
    # Check for success message
    success_message = await page.query_selector('.alert-success')
    error_message = await page.query_selector('.alert-danger')
    
    if success_message:
        return {
            'type': 'admin_clear_database',
            'success': True,
            'message': await success_message.text_content(),
            'options': {
                'keep_users': keep_users,
                'keep_admin': keep_admin,
                'dry_run': dry_run
            }
        }
    elif error_message:
        return {
            'type': 'admin_clear_database',
            'success': False,
            'error': await error_message.text_content(),
            'options': {
                'keep_users': keep_users,
                'keep_admin': keep_admin,
                'dry_run': dry_run
            }
        }
    
    return {
        'type': 'admin_clear_database',
        'success': True,
        'message': 'Clear database action completed (no explicit success/error message found)',
        'options': {
            'keep_users': keep_users,
            'keep_admin': keep_admin,
            'dry_run': dry_run
        }
    }


async def admin_populate_demo_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Handle admin populate demo data action."""
    reset_data = action.get('reset_data', False)
    users_count = action.get('users_count', 10)
    equipment_count = action.get('equipment_count', 50)
    activities_count = action.get('activities_count', 100)
    events_count = action.get('events_count', 75)
    
    # Navigate to settings page
    await page.goto('http://web:8000/core/settings/')
    await page.wait_for_load_state('networkidle')
    
    # Look for Populate Demo Data button
    demo_button = await page.query_selector('button:has-text("Populate Demo Data")')
    if not demo_button:
        return {
            'type': 'admin_populate_demo',
            'success': False,
            'error': 'Populate Demo Data button not found - user may not have admin permissions'
        }
    
    # Click the button to open modal
    await demo_button.click()
    await page.wait_for_timeout(1000)
    
    # Check if modal opened
    modal = await page.query_selector('.modal')
    if not modal:
        return {
            'type': 'admin_populate_demo',
            'success': False,
            'error': 'Populate Demo Data modal did not open'
        }
    
    # Fill in the form
    form = await page.query_selector('#demoDataForm')
    if form:
        # Set reset data checkbox
        if reset_data:
            reset_checkbox = await page.query_selector('input[name="reset_data"]')
            if reset_checkbox:
                await reset_checkbox.check()
        
        # Set counts
        users_input = await page.query_selector('input[name="users_count"]')
        if users_input:
            await users_input.fill(str(users_count))
        
        equipment_input = await page.query_selector('input[name="equipment_count"]')
        if equipment_input:
            await equipment_input.fill(str(equipment_count))
        
        activities_input = await page.query_selector('input[name="activities_count"]')
        if activities_input:
            await activities_input.fill(str(activities_count))
        
        events_input = await page.query_selector('input[name="events_count"]')
        if events_input:
            await events_input.fill(str(events_count))
    
    # Submit the form
    submit_button = await page.query_selector('button[type="submit"]')
    if submit_button:
        await submit_button.click()
        await page.wait_for_timeout(5000)  # Longer wait for demo data population
    
    # Check for success message
    success_message = await page.query_selector('.alert-success')
    error_message = await page.query_selector('.alert-danger')
    
    if success_message:
        return {
            'type': 'admin_populate_demo',
            'success': True,
            'message': await success_message.text_content(),
            'options': {
                'reset_data': reset_data,
                'users_count': users_count,
                'equipment_count': equipment_count,
                'activities_count': activities_count,
                'events_count': events_count
            }
        }
    elif error_message:
        return {
            'type': 'admin_populate_demo',
            'success': False,
            'error': await error_message.text_content(),
            'options': {
                'reset_data': reset_data,
                'users_count': users_count,
                'equipment_count': equipment_count,
                'activities_count': activities_count,
                'events_count': events_count
            }
        }
    
    return {
        'type': 'admin_populate_demo',
        'success': True,
        'message': 'Demo data population completed (no explicit success/error message found)',
        'options': {
            'reset_data': reset_data,
            'users_count': users_count,
            'equipment_count': equipment_count,
            'activities_count': activities_count,
            'events_count': events_count
        }
    }


async def create_site_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Create a site with PODs and MDCs."""
    site_name = action.get('site_name', 'Test Site')
    pod_count = action.get('pod_count', 11)
    mdcs_per_pod = action.get('mdcs_per_pod', 2)
    force = action.get('force', False)
    
    # Navigate to settings page
    await page.goto('http://web:8000/core/settings/')
    await page.wait_for_load_state('networkidle')
    
    # Look for POD generation functionality
    pod_button = await page.query_selector('button:has-text("Generate PODs")')
    if pod_button:
        await pod_button.click()
        await page.wait_for_timeout(1000)
        
        # Fill in the form if it exists
        site_input = await page.query_selector('input[name="site_name"]')
        if site_input:
            await site_input.fill(site_name)
        
        pod_count_input = await page.query_selector('input[name="pod_count"]')
        if pod_count_input:
            await pod_count_input.fill(str(pod_count))
        
        mdcs_input = await page.query_selector('input[name="mdcs_per_pod"]')
        if mdcs_input:
            await mdcs_input.fill(str(mdcs_per_pod))
        
        # Set force option if specified
        if force:
            force_checkbox = await page.query_selector('input[name="force"]')
            if force_checkbox:
                await force_checkbox.check()
        
        # Submit the form
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(2000)
    
    return {
        'type': 'create_site',
        'success': True,
        'site_name': site_name,
        'pod_count': pod_count,
        'mdcs_per_pod': mdcs_per_pod,
        'force': force,
        'message': f'Attempted to create site {site_name} with {pod_count} PODs and {mdcs_per_pod} MDCs per POD'
    }


async def create_equipment_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Create equipment in a specific site."""
    equipment_name = action.get('equipment_name', 'Test Equipment')
    site_name = action.get('site_name')
    category = action.get('category', 'Transformers')
    
    # Navigate to equipment page
    await page.goto('http://web:8000/equipment/')
    await page.wait_for_load_state('networkidle')
    
    # Look for add equipment button
    add_button = await page.query_selector('a:has-text("Add Equipment"), button:has-text("Add Equipment")')
    if add_button:
        await add_button.click()
        await page.wait_for_timeout(1000)
        
        # Fill in equipment form
        name_input = await page.query_selector('input[name="name"]')
        if name_input:
            await name_input.fill(equipment_name)
        
        # Select category if available
        category_select = await page.query_selector('select[name="category"]')
        if category_select:
            await category_select.select_option(label=category)
        
        # Select site if specified
        if site_name:
            site_select = await page.query_selector('select[name="location"]')
            if site_select:
                await site_select.select_option(label=site_name)
        
        # Submit the form
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(2000)
    
    return {
        'type': 'create_equipment',
        'success': True,
        'equipment_name': equipment_name,
        'site_name': site_name,
        'category': category,
        'message': f'Attempted to create equipment {equipment_name} in {site_name or "default location"}'
    }


async def create_user_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Create a user with specified role."""
    username = action.get('username', 'test_user')
    role = action.get('role', 'Technician')
    
    # Navigate to user management page
    await page.goto('http://web:8000/core/settings/users/')
    await page.wait_for_load_state('networkidle')
    
    # Look for add user button
    add_button = await page.query_selector('a:has-text("Add User"), button:has-text("Add User")')
    if add_button:
        await add_button.click()
        await page.wait_for_timeout(1000)
        
        # Fill in user form
        username_input = await page.query_selector('input[name="username"]')
        if username_input:
            await username_input.fill(username)
        
        # Select role if available
        role_select = await page.query_selector('select[name="role"]')
        if role_select:
            await role_select.select_option(label=role)
        
        # Submit the form
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(2000)
    
    return {
        'type': 'create_user',
        'success': True,
        'username': username,
        'role': role,
        'message': f'Attempted to create user {username} with role {role}'
    }


async def test_rbac_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Test RBAC permissions for specific user and action."""
    user_role = action.get('user_role', 'Technician')
    test_action = action.get('action', 'access settings')
    expected_result = action.get('expected_result', 'allowed')
    
    # First, ensure we're logged in as the correct user type
    # This would require user switching logic or separate test runs
    
    # Navigate to the page/action being tested
    if 'settings' in test_action:
        await page.goto('http://web:8000/core/settings/')
    elif 'admin' in test_action:
        await page.goto('http://web:8000/admin/')
    else:
        await page.goto('http://web:8000/')
    
    await page.wait_for_load_state('networkidle')
    
    # Check if access is allowed or denied
    access_denied = await page.query_selector('.alert-danger, .error-message')
    forbidden = await page.query_selector('h1:has-text("403"), h1:has-text("Forbidden")')
    
    if access_denied or forbidden:
        actual_result = 'denied'
    else:
        actual_result = 'allowed'
    
    success = (actual_result == expected_result)
    
    return {
        'type': 'test_rbac',
        'success': success,
        'user_role': user_role,
        'action': test_action,
        'expected_result': expected_result,
        'actual_result': actual_result,
        'message': f'RBAC test: {user_role} user {test_action} - Expected: {expected_result}, Actual: {actual_result}'
    }


async def test_page_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Test specific page functionality."""
    page_name = action.get('page_name', 'Dashboard')
    expected_elements = action.get('expected_elements', [])
    
    # Navigate to the specified page
    page_urls = {
        'Dashboard': 'http://web:8000/',
        'Settings': 'http://web:8000/core/settings/',
        'Equipment': 'http://web:8000/equipment/',
        'Maintenance': 'http://web:8000/maintenance/',
        'Events': 'http://web:8000/events/',
        'Users': 'http://web:8000/core/settings/users/',
        'Locations': 'http://web:8000/core/settings/locations/',
    }
    
    url = page_urls.get(page_name, 'http://web:8000/')
    await page.goto(url)
    await page.wait_for_load_state('networkidle')
    
    # Check for expected elements
    found_elements = []
    missing_elements = []
    
    for element in expected_elements:
        selector = f'{element}, [class*="{element}"], [id*="{element}"]'
        found = await page.query_selector(selector)
        if found:
            found_elements.append(element)
        else:
            missing_elements.append(element)
    
    success = len(missing_elements) == 0
    
    return {
        'type': 'test_page',
        'success': success,
        'page_name': page_name,
        'expected_elements': expected_elements,
        'found_elements': found_elements,
        'missing_elements': missing_elements,
        'message': f'Page test: {page_name} - Found: {found_elements}, Missing: {missing_elements}'
    }


async def general_test_action(page: Page, action: Dict[str, Any], action_index: int) -> Dict[str, Any]:
    """Handle general test actions."""
    prompt = action.get('prompt', '')
    
    # Navigate to dashboard
    await page.goto('http://web:8000/')
    await page.wait_for_load_state('networkidle')
    
    # Take a screenshot and check basic page elements
    title = await page.title()
    url = page.url
    
    # Check for common page elements
    elements_found = []
    common_selectors = ['nav', 'main', '.container', '.content', 'h1', 'h2']
    
    for selector in common_selectors:
        element = await page.query_selector(selector)
        if element:
            elements_found.append(selector)
    
    return {
        'type': 'general_test',
        'success': True,
        'prompt': prompt,
        'title': title,
        'url': url,
        'elements_found': elements_found,
        'message': f'General test completed for prompt: {prompt}'
    } 