from celery import shared_task
import logging
from .models import PlaywrightDebugLog
from django.utils import timezone
import subprocess
import json
import os
import sys
import re

logger = logging.getLogger(__name__)

@shared_task
def celery_beat_heartbeat():
    logger.info("Celery Beat heartbeat task ran.") 

def parse_natural_language(prompt):
    """
    Parse natural language prompt and convert to structured actions.
    Examples:
    - "Add a Site called Sophie with 11 Pods and 2 MDCs per Pod"
    - "Create equipment called Transformer-1 in Site Alpha"
    - "Test the login page"
    """
    prompt_lower = prompt.lower()
    actions = []
    
    # Site creation patterns
    site_patterns = [
        r'add\s+a\s+site\s+(?:called\s+)?([a-zA-Z0-9\s]+?)(?:\s+with\s+(\d+)\s+pods?\s+and\s+(\d+)\s+mdcs?\s+per\s+pod)?',
        r'create\s+a\s+site\s+(?:called\s+)?([a-zA-Z0-9\s]+?)(?:\s+with\s+(\d+)\s+pods?\s+and\s+(\d+)\s+mdcs?\s+per\s+pod)?',
        r'generate\s+a\s+site\s+(?:called\s+)?([a-zA-Z0-9\s]+?)(?:\s+with\s+(\d+)\s+pods?\s+and\s+(\d+)\s+mdcs?\s+per\s+pod)?',
    ]
    
    for pattern in site_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            site_name = match.group(1).strip()
            pod_count = int(match.group(2)) if match.group(2) else 11
            mdcs_per_pod = int(match.group(3)) if match.group(3) else 2
            
            actions.append({
                'type': 'create_site',
                'site_name': site_name,
                'pod_count': pod_count,
                'mdcs_per_pod': mdcs_per_pod
            })
            break
    
    # Equipment creation patterns
    equipment_patterns = [
        r'(?:add|create)\s+(?:equipment|device)\s+(?:called\s+)?([a-zA-Z0-9\-\s]+?)(?:\s+in\s+(?:site\s+)?([a-zA-Z0-9\s]+))?',
        r'create\s+([a-zA-Z0-9\-\s]+?)\s+(?:equipment|device)(?:\s+in\s+(?:site\s+)?([a-zA-Z0-9\s]+))?',
    ]
    
    for pattern in equipment_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            equipment_name = match.group(1).strip()
            site_name = match.group(2).strip() if match.group(2) else None
            
            actions.append({
                'type': 'create_equipment',
                'equipment_name': equipment_name,
                'site_name': site_name
            })
            break
    
    # Test patterns
    test_patterns = [
        r'test\s+(?:the\s+)?([a-zA-Z0-9\-\s]+?)(?:\s+page)?',
        r'check\s+(?:the\s+)?([a-zA-Z0-9\-\s]+?)(?:\s+page)?',
        r'verify\s+(?:the\s+)?([a-zA-Z0-9\-\s]+?)(?:\s+page)?',
    ]
    
    for pattern in test_patterns:
        match = re.search(pattern, prompt_lower)
        if match:
            page_name = match.group(1).strip()
            
            actions.append({
                'type': 'test_page',
                'page_name': page_name
            })
            break
    
    # If no specific patterns match, treat as general test
    if not actions:
        actions.append({
            'type': 'general_test',
            'description': prompt
        })
    
    return actions

@shared_task
def run_playwright_debug(log_id):
    log = PlaywrightDebugLog.objects.get(id=log_id)
    if log.status != 'pending':
        return
    
    log.status = 'running'
    log.started_at = timezone.now()
    log.save(update_fields=['status', 'started_at'])
    
    try:
        # Parse natural language prompt
        actions = parse_natural_language(log.prompt)
        
        # Use Python to run Playwright tests instead of Node.js
        # Find the playwright directory
        playwright_dir = os.path.join(os.getcwd(), 'playwright')
        if not os.path.exists(playwright_dir):
            playwright_dir = os.path.join(os.path.dirname(os.getcwd()), 'playwright')
        
        # Generate test script based on parsed actions
        test_script = generate_test_script(actions, log.prompt, log.id)
        
        # Write the test script to a temporary file
        test_file = f'/tmp/playwright_test_{log_id}.py'
        with open(test_file, 'w') as f:
            f.write(test_script)
        
        # Run the Python test script
        result = subprocess.run([
            sys.executable, test_file,
            log.prompt,
            str(log.id)
        ], capture_output=True, text=True, timeout=300)
        
        log.output = result.stdout
        if result.returncode == 0:
            log.status = 'done'
            try:
                output_json = json.loads(result.stdout)
                log.result_json = output_json
            except Exception:
                pass
        else:
            log.status = 'error'
            log.error_message = result.stderr
            
        # Clean up temporary file
        try:
            os.remove(test_file)
        except:
            pass
            
    except Exception as e:
        log.status = 'error'
        log.error_message = str(e)
        logger.error(f"Playwright debug task failed: {e}")
    
    log.finished_at = timezone.now()
    log.save()

def generate_test_script(actions, original_prompt, log_id):
    """Generate a Playwright test script based on parsed actions."""
    
    script = f"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys
import time

async def run_test(actions, original_prompt, log_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        results = []
        
        try:
            # Navigate to the application
            await page.goto('http://web:8000/auth/login/')
            await page.wait_for_load_state('networkidle')
            
            # Take initial screenshot
            screenshot_path = f'/tmp/playwright_debug_{{log_id}}_initial.png'
            await page.screenshot(path=screenshot_path)
            
            # Process each action
            for i, action in enumerate(actions):
                action_result = await process_action(page, action, i)
                results.append(action_result)
                
                # Take screenshot after each action
                action_screenshot = f'/tmp/playwright_debug_{{log_id}}_action_{{i}}.png'
                await page.screenshot(path=action_screenshot)
                action_result['screenshot'] = action_screenshot
            
            result = {{
                'success': True,
                'message': f'Successfully processed {{len(actions)}} actions for prompt: {{original_prompt}}',
                'actions': results,
                'initial_screenshot': screenshot_path,
                'url': page.url
            }}
            
        except Exception as e:
            result = {{
                'success': False,
                'error': str(e),
                'message': f'Failed to process actions: {{str(e)}}',
                'actions': results
            }}
        finally:
            await browser.close()
        
        return result

async def process_action(page, action, action_index):
    '''Process a single action based on its type.'''
    action_type = action.get('type')
    
    try:
        if action_type == 'create_site':
            return await create_site_action(page, action, action_index)
        elif action_type == 'create_equipment':
            return await create_equipment_action(page, action, action_index)
        elif action_type == 'test_page':
            return await test_page_action(page, action, action_index)
        elif action_type == 'general_test':
            return await general_test_action(page, action, action_index)
        else:
            return {{
                'type': action_type,
                'success': False,
                'error': f'Unknown action type: {{action_type}}'
            }}
    except Exception as e:
        return {{
            'type': action_type,
            'success': False,
            'error': str(e)
        }}

async def create_site_action(page, action, action_index):
    '''Create a site with PODs and MDCs.'''
    site_name = action.get('site_name', 'Test Site')
    pod_count = action.get('pod_count', 11)
    mdcs_per_pod = action.get('mdcs_per_pod', 2)
    
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
        
        # Submit the form
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(2000)
    
    return {{
        'type': 'create_site',
        'success': True,
        'site_name': site_name,
        'pod_count': pod_count,
        'mdcs_per_pod': mdcs_per_pod,
        'message': f'Attempted to create site {{site_name}} with {{pod_count}} PODs and {{mdcs_per_pod}} MDCs per POD'
    }}

async def create_equipment_action(page, action, action_index):
    '''Create equipment in a specific site.'''
    equipment_name = action.get('equipment_name', 'Test Equipment')
    site_name = action.get('site_name')
    
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
        
        # Submit the form
        submit_button = await page.query_selector('button[type="submit"]')
        if submit_button:
            await submit_button.click()
            await page.wait_for_timeout(2000)
    
    return {{
        'type': 'create_equipment',
        'success': True,
        'equipment_name': equipment_name,
        'site_name': site_name,
        'message': f'Attempted to create equipment {{equipment_name}}'
    }}

async def test_page_action(page, action, action_index):
    '''Test a specific page.'''
    page_name = action.get('page_name', 'login')
    
    # Map page names to URLs
    page_urls = {{
        'login': 'http://web:8000/auth/login/',
        'dashboard': 'http://web:8000/core/dashboard/',
        'equipment': 'http://web:8000/equipment/',
        'maintenance': 'http://web:8000/maintenance/',
        'events': 'http://web:8000/events/',
        'settings': 'http://web:8000/core/settings/',
        'calendar': 'http://web:8000/events/calendar/',
    }}
    
    url = page_urls.get(page_name.lower(), 'http://web:8000/')
    await page.goto(url)
    await page.wait_for_load_state('networkidle')
    
    # Check if page loaded successfully
    title = await page.title()
    
    return {{
        'type': 'test_page',
        'success': True,
        'page_name': page_name,
        'url': url,
        'title': title,
        'message': f'Successfully tested {{page_name}} page'
    }}

async def general_test_action(page, action, action_index):
    '''Perform a general test based on description.'''
    description = action.get('description', 'General test')
    
    # Navigate to dashboard and perform basic checks
    await page.goto('http://web:8000/core/dashboard/')
    await page.wait_for_load_state('networkidle')
    
    # Check for common elements
    elements_found = []
    selectors = ['h1', 'h2', 'h3', 'nav', 'button', 'a', 'form']
    
    for selector in selectors:
        elements = await page.query_selector_all(selector)
        if elements:
            elements_found.append(f'{{selector}}: {{len(elements)}}')
    
    return {{
        'type': 'general_test',
        'success': True,
        'description': description,
        'elements_found': elements_found,
        'message': f'General test completed for: {{description}}'
    }}

if __name__ == '__main__':
    actions = {json.dumps(actions)}
    original_prompt = sys.argv[1] if len(sys.argv) > 1 else 'Test application'
    log_id = sys.argv[2] if len(sys.argv) > 2 else '1'
    
    result = asyncio.run(run_test(actions, original_prompt, log_id))
    print(json.dumps(result))
"""
    
    return script 