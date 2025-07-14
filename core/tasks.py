from celery import shared_task
import logging
from .models import PlaywrightDebugLog
from django.utils import timezone
import subprocess
import json
import os
import sys

logger = logging.getLogger(__name__)

@shared_task
def celery_beat_heartbeat():
    logger.info("Celery Beat heartbeat task ran.") 

@shared_task
def run_playwright_debug(log_id):
    log = PlaywrightDebugLog.objects.get(id=log_id)
    if log.status != 'pending':
        return
    
    log.status = 'running'
    log.started_at = timezone.now()
    log.save(update_fields=['status', 'started_at'])
    
    try:
        # Use Python to run Playwright tests instead of Node.js
        # Find the playwright directory
        playwright_dir = os.path.join(os.getcwd(), 'playwright')
        if not os.path.exists(playwright_dir):
            playwright_dir = os.path.join(os.path.dirname(os.getcwd()), 'playwright')
        
        # Run a simple Playwright test using Python
        test_script = f"""
import asyncio
from playwright.async_api import async_playwright
import json
import sys

async def run_test(prompt, log_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Navigate to the login page using internal Docker hostname
            await page.goto('http://web:8000/auth/login/')
            await page.wait_for_load_state('networkidle')
            
            # Take a screenshot
            screenshot_path = f'/tmp/playwright_debug_{{log_id}}.png'
            await page.screenshot(path=screenshot_path)
            
            # Check if login form exists
            login_form = await page.query_selector('form')
            form_exists = login_form is not None
            
            result = {{
                'success': True,
                'message': f'Successfully tested login page for prompt: {{prompt}}',
                'screenshot_path': screenshot_path,
                'form_exists': form_exists,
                'url': page.url
            }}
            
        except Exception as e:
            result = {{
                'success': False,
                'error': str(e),
                'message': f'Failed to test login page: {{str(e)}}'
            }}
        finally:
            await browser.close()
        
        return result

if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'Test login page'
    log_id = sys.argv[2] if len(sys.argv) > 2 else '1'
    
    result = asyncio.run(run_test(prompt, log_id))
    print(json.dumps(result))
"""
        
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