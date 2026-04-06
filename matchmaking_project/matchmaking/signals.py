from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import UserPlan, FeatureFlag


@receiver(post_save, sender=User)
def create_user_plan(sender, instance, created, **kwargs):
    """
    Automatically create a UserPlan with initial free credits
    whenever a new user registers.
    """
    if created:
        config = FeatureFlag.get()
        UserPlan.objects.create(
            user=instance,
            free_credits=config.initial_free_credits,
            paid_credits=0,
        )