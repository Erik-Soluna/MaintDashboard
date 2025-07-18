from celery import shared_task
import logging
import asyncio
import json
import requests
from .models import PlaywrightDebugLog, PortainerConfig
from django.utils import timezone
from .playwright_orchestrator import run_natural_language_test, run_rbac_test_suite

logger = logging.getLogger(__name__)

@shared_task
def celery_beat_heartbeat():
    logger.info("Celery Beat heartbeat task ran.")

@shared_task
def run_playwright_debug(log_id):
    """
    Run Playwright debug test using the new modular orchestration system.
    """
    try:
        log = PlaywrightDebugLog.objects.get(id=log_id)
        if log.status != 'pending':
            return
        
        log.status = 'running'
        log.started_at = timezone.now()
        log.save(update_fields=['status', 'started_at'])
        
        # Run the natural language test using our new orchestrator
        # We need to run this in an event loop since it's async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                run_natural_language_test(
                    prompt=log.prompt,
                    user_role='admin',  # Default to admin for now
                    username='admin',
                    password='temppass123'
                )
            )
            
            # Store results
            log.output = json.dumps(result, indent=2)
            log.result_json = result
            
            if result.get('success', False):
                log.status = 'done'
            else:
                log.status = 'error'
                log.error_message = result.get('error', 'Test failed')
                
        finally:
            loop.close()
            
    except PlaywrightDebugLog.DoesNotExist:
        logger.error(f"PlaywrightDebugLog with id {log_id} not found")
        return
    except Exception as e:
        logger.error(f"Playwright debug task failed: {e}")
        try:
            log.status = 'error'
            log.error_message = str(e)
        except:
            pass
    
    finally:
        try:
            log.finished_at = timezone.now()
            log.save()
        except:
            pass

@shared_task
def run_rbac_test_suite_task():
    """
    Run comprehensive RBAC test suite.
    """
    try:
        # Run the RBAC test suite
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(run_rbac_test_suite())
            logger.info(f"RBAC test suite completed: {result.get('success_rate', 0)}% success rate")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"RBAC test suite failed: {e}")
        return {'error': str(e)}

@shared_task
def run_natural_language_test_task(prompt: str, user_role: str = "admin", 
                                  username: str = "admin", password: str = "temppass123"):
    """
    Run a natural language test as a Celery task.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                run_natural_language_test(prompt, user_role, username, password)
            )
            logger.info(f"Natural language test completed: {result.get('success', False)}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Natural language test failed: {e}")
        return {'error': str(e)}

@shared_task
def auto_update_portainer_stack():
    """
    Automatically check for and pull the newest version based on polling frequency.
    """
    try:
        config = PortainerConfig.get_config()
        
        # Check if polling is enabled
        if not config.polling_frequency or config.polling_frequency == 'disabled':
            logger.info("Auto-update polling is disabled")
            return {'status': 'disabled'}
        
        # Check if webhook URL is configured
        if not config.portainer_url:
            logger.warning("Auto-update failed: No webhook URL configured")
            return {'status': 'error', 'message': 'No webhook URL configured'}
        
        # Get image tag (default to 'latest')
        image_tag = config.image_tag or 'latest'
        
        # Build webhook URL with tag parameter
        webhook_url_with_tag = f"{config.portainer_url}?tag={image_tag}"
        
        # Prepare headers with webhook secret if available
        headers = {}
        if config.webhook_secret:
            headers['X-Webhook-Secret'] = config.webhook_secret
        
        logger.info(f"Auto-updating stack with tag '{image_tag}' via webhook")
        
        # Call the webhook URL to trigger stack update
        webhook_response = requests.post(
            webhook_url_with_tag,
            headers=headers,
            json={'action': 'auto_update', 'timestamp': timezone.now().isoformat()},
            timeout=30
        )
        
        logger.info(f"Auto-update webhook response status: {webhook_response.status_code}")
        
        if webhook_response.status_code in [200, 202, 204]:
            logger.info("Auto-update successful")
            return {
                'status': 'success', 
                'message': f'Auto-update triggered successfully with tag {image_tag}',
                'response_code': webhook_response.status_code
            }
        else:
            logger.error(f"Auto-update failed with status: {webhook_response.status_code}")
            return {
                'status': 'error', 
                'message': f'Auto-update failed: {webhook_response.status_code}',
                'response_code': webhook_response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error in auto-update: {str(e)}")
        return {'status': 'error', 'message': f'Network error: {str(e)}'}
    except Exception as e:
        logger.error(f"Unexpected error in auto-update: {str(e)}")
        return {'status': 'error', 'message': f'Error: {str(e)}'}