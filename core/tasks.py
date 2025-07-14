from celery import shared_task
import logging
from .models import PlaywrightDebugLog
from django.utils import timezone
import subprocess
import json

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
        # Run the Playwright smart runner with the prompt
        # (Assume a script: run_smart_test.js that takes --prompt and --log-id)
        result = subprocess.run([
            'node', 'run_smart_test.js',
            '--prompt', log.prompt,
            '--log-id', str(log.id)
        ], capture_output=True, text=True, timeout=600)
        log.output = result.stdout
        if result.returncode == 0:
            log.status = 'done'
        else:
            log.status = 'error'
            log.error_message = result.stderr
        # Optionally parse result JSON from output
        try:
            output_json = json.loads(result.stdout)
            log.result_json = output_json
        except Exception:
            pass
    except Exception as e:
        log.status = 'error'
        log.error_message = str(e)
    log.finished_at = timezone.now()
    log.save() 