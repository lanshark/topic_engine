from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
import logging
from .models import Content

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Content)
def handle_new_content(sender, instance, created, **kwargs):
    """Queue content for prediction when new articles are created"""
    if created:
        # Use cache to batch process articles
        cache_key = 'pending_prediction_content'
        pending_ids = cache.get(cache_key, set())
        pending_ids.add(instance.id)
        cache.set(cache_key, pending_ids, timeout=300)  # 5 minute timeout
        
        # Schedule processing if we have enough items
        if len(pending_ids) >= 50:
            from django.core.management import call_command
            content_ids = list(pending_ids)
            cache.delete(cache_key)
            # Run synchronously for now, can be moved to async task later
            call_command('predict_topics', content_ids=content_ids)
            logger.info(f"Processed predictions for batch of {len(content_ids)} articles")
