from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def celery_beat_heartbeat():
    logger.info("Celery Beat heartbeat task ran.") 