from celery import shared_task
import logging
import asyncio
import json
from .models import PlaywrightDebugLog
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