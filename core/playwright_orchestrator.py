"""
Playwright test orchestrator for managing test execution, logging, and result collection.
Handles the overall flow of natural language test execution.
"""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from .playwright_parser import parse_natural_language
from .playwright_actions import process_action

logger = logging.getLogger(__name__)


class PlaywrightOrchestrator:
    """Orchestrates Playwright test execution with natural language prompts."""
    
    def __init__(self, base_url: str = "http://web:8000", headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.results = []
        self.screenshots = []
        self.html_dumps = []
        
    async def run_test(self, prompt: str, user_role: str = "admin", 
                      username: str = "admin", password: str = "temppass123") -> Dict[str, Any]:
        """
        Run a complete test based on natural language prompt.
        
        Args:
            prompt: Natural language description of what to test
            user_role: Role of the user to test as
            username: Username for login
            password: Password for login
            
        Returns:
            Dictionary with test results, screenshots, and logs
        """
        start_time = datetime.now()
        
        try:
            # Parse the natural language prompt
            actions = parse_natural_language(prompt)
            logger.info(f"Parsed prompt into {len(actions)} actions")
            
            # Run Playwright test
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context()
                page = await context.new_page()
                
                # Login as specified user
                await self._login_user(page, username, password)
                
                # Execute each action
                action_results = []
                for i, action in enumerate(actions):
                    logger.info(f"Executing action {i+1}/{len(actions)}: {action.get('type')}")
                    
                    # Take screenshot before action
                    screenshot_path = await self._take_screenshot(page, f"before_action_{i+1}")
                    
                    # Execute action
                    result = await process_action(page, action, i)
                    action_results.append(result)
                    
                    # Take screenshot after action
                    screenshot_path = await self._take_screenshot(page, f"after_action_{i+1}")
                    
                    # Add HTML dump
                    html_dump_path = await self._dump_html(page, f"action_{i+1}")
                    
                    # Wait between actions
                    await page.wait_for_timeout(1000)
                
                await browser.close()
            
            # Compile results
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            test_result = {
                'prompt': prompt,
                'user_role': user_role,
                'username': username,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration': duration,
                'actions': actions,
                'action_results': action_results,
                'screenshots': self.screenshots,
                'html_dumps': self.html_dumps,
                'success': all(result.get('success', False) for result in action_results),
                'summary': self._generate_summary(actions, action_results)
            }
            
            logger.info(f"Test completed in {duration:.2f}s with {len(action_results)} actions")
            return test_result
            
        except Exception as e:
            logger.error(f"Error running test: {e}")
            return {
                'prompt': prompt,
                'user_role': user_role,
                'username': username,
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': (datetime.now() - start_time).total_seconds(),
                'success': False,
                'error': str(e),
                'screenshots': self.screenshots,
                'html_dumps': self.html_dumps
            }
    
    async def _login_user(self, page: Page, username: str, password: str):
        """Login as specified user."""
        try:
            await page.goto(f"{self.base_url}/accounts/login/")
            await page.wait_for_load_state('networkidle')
            
            # Fill login form
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            
            # Submit form
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
            
            # Check if login was successful
            error_message = await page.query_selector('.alert-danger')
            if error_message:
                logger.warning(f"Login failed for user {username}")
            else:
                logger.info(f"Successfully logged in as {username}")
                
        except Exception as e:
            logger.error(f"Error during login: {e}")
    
    async def _take_screenshot(self, page: Page, name: str) -> str:
        """Take a screenshot and save it."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%fZ")
            filename = f"{name}_{timestamp}.png"
            
            # Create screenshots directory if it doesn't exist
            screenshots_dir = "playwright/screenshots/natural-language"
            os.makedirs(screenshots_dir, exist_ok=True)
            
            screenshot_path = os.path.join(screenshots_dir, filename)
            await page.screenshot(path=screenshot_path)
            
            self.screenshots.append({
                'name': name,
                'path': screenshot_path,
                'timestamp': timestamp
            })
            
            logger.info(f"Screenshot saved: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return ""
    
    async def _dump_html(self, page: Page, name: str) -> str:
        """Dump page HTML for debugging."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S-%fZ")
            filename = f"{name}_{timestamp}.html"
            
            # Create html-dumps directory if it doesn't exist
            html_dir = "playwright/html-dumps/natural-language"
            os.makedirs(html_dir, exist_ok=True)
            
            html_path = os.path.join(html_dir, filename)
            html_content = await page.content()
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.html_dumps.append({
                'name': name,
                'path': html_path,
                'timestamp': timestamp
            })
            
            logger.info(f"HTML dump saved: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"Error dumping HTML: {e}")
            return ""
    
    def _generate_summary(self, actions: List[Dict], results: List[Dict]) -> Dict[str, Any]:
        """Generate a summary of test results."""
        total_actions = len(actions)
        successful_actions = sum(1 for result in results if result.get('success', False))
        failed_actions = total_actions - successful_actions
        
        action_summary = []
        for i, (action, result) in enumerate(zip(actions, results)):
            action_summary.append({
                'index': i + 1,
                'type': action.get('type'),
                'description': action.get('description'),
                'success': result.get('success', False),
                'message': result.get('message', ''),
                'error': result.get('error', '')
            })
        
        return {
            'total_actions': total_actions,
            'successful_actions': successful_actions,
            'failed_actions': failed_actions,
            'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
            'action_summary': action_summary
        }


async def run_natural_language_test(prompt: str, user_role: str = "admin", 
                                   username: str = "admin", password: str = "temppass123") -> Dict[str, Any]:
    """
    Convenience function to run a natural language test.
    
    Args:
        prompt: Natural language description of what to test
        user_role: Role of the user to test as
        username: Username for login
        password: Password for login
        
    Returns:
        Dictionary with test results
    """
    orchestrator = PlaywrightOrchestrator()
    return await orchestrator.run_test(prompt, user_role, username, password)


async def run_rbac_test_suite() -> Dict[str, Any]:
    """
    Run a comprehensive RBAC test suite.
    
    Returns:
        Dictionary with RBAC test results
    """
    test_cases = [
        {
            'prompt': 'Test admin user can clear database',
            'user_role': 'admin',
            'username': 'admin',
            'expected_result': 'allowed'
        },
        {
            'prompt': 'Test technician user cannot clear database',
            'user_role': 'technician',
            'username': 'demo_technician_1',
            'expected_result': 'denied'
        },
        {
            'prompt': 'Test manager user can populate demo data',
            'user_role': 'manager',
            'username': 'demo_manager_1',
            'expected_result': 'allowed'
        },
        {
            'prompt': 'Test viewer user cannot access settings',
            'user_role': 'viewer',
            'username': 'demo_viewer_1',
            'expected_result': 'denied'
        }
    ]
    
    orchestrator = PlaywrightOrchestrator()
    results = []
    
    for test_case in test_cases:
        logger.info(f"Running RBAC test: {test_case['prompt']}")
        result = await orchestrator.run_test(
            test_case['prompt'],
            test_case['user_role'],
            test_case['username']
        )
        results.append({
            'test_case': test_case,
            'result': result
        })
    
    # Generate RBAC summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r['result']['success'])
    
    return {
        'test_suite': 'RBAC',
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': total_tests - passed_tests,
        'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
        'results': results
    } 