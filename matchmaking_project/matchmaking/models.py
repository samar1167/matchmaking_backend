from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='astro_profile')
    date_of_birth  = models.DateField()
    time_of_birth  = models.TimeField()
    place_of_birth = models.CharField(max_length=255)
    latitude       = models.FloatField(null=True, blank=True)
    longitude      = models.FloatField(null=True, blank=True)
    timezone       = models.CharField(max_length=50, default='UTC')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['user'])]

    def __str__(self):
        return f"{self.user.username}'s profile"

    def get_birth_datetime(self):
        return datetime.combine(self.date_of_birth, self.time_of_birth)


class PrivatePerson(models.Model):
    owner          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_persons')
    name           = models.CharField(max_length=255)
    nickname       = models.CharField(max_length=100, blank=True)
    notes          = models.TextField(blank=True)
    date_of_birth  = models.DateField()
    time_of_birth  = models.TimeField(null=True, blank=True)
    place_of_birth = models.CharField(max_length=255, blank=True)
    latitude       = models.FloatField(null=True, blank=True)
    longitude      = models.FloatField(null=True, blank=True)
    timezone       = models.CharField(max_length=50, default='UTC')
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('owner', 'name')
        indexes = [models.Index(fields=['owner'])]

    def __str__(self):
        return f"{self.name} (private, owner: {self.owner.username})"

    def get_birth_datetime(self):
        time = self.time_of_birth or datetime.min.time()
        return datetime.combine(self.date_of_birth, time)


class CompatibilityScore(models.Model):
    user                   = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='compatibility_checks')
    matched_user           = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='matched_against')
    matched_private_person = models.ForeignKey(PrivatePerson, on_delete=models.CASCADE, null=True, blank=True, related_name='compatibility_checks')
    overall_score          = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    sun_compatibility      = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    moon_compatibility     = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    venus_compatibility    = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    mars_compatibility     = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    description            = models.TextField(blank=True)
    api_response           = models.JSONField(null=True, blank=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user']), models.Index(fields=['overall_score'])]
        constraints = [
            models.CheckConstraint(
                name='one_match_target_required',
                check=(
                    models.Q(matched_user__isnull=False, matched_private_person__isnull=True) |
                    models.Q(matched_user__isnull=True,  matched_private_person__isnull=False)
                )
            )
        ]

    def __str__(self):
        return f"{self.user} vs {self.get_match_target()} ({self.overall_score}%)"

    def get_match_target(self):
        return self.matched_user or self.matched_private_person

    def is_private_match(self):
        return self.matched_private_person is not None
