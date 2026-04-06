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
    

class CompatibilityParameter(models.Model):
    """
    Admin defines each compatibility parameter and whether it is free or paid.
    e.g. sun=free, moon=free, venus=paid, mars=paid, jupiter=paid ...
    """
    key        = models.CharField(max_length=50, unique=True,
                     help_text="Matches the key in the astrology API response e.g. 'sun_compatibility'")
    label      = models.CharField(max_length=100,
                     help_text="Human readable label e.g. 'Sun Compatibility'")
    is_free    = models.BooleanField(default=False,
                     help_text="Free users can see this parameter")
    order      = models.PositiveIntegerField(default=0,
                     help_text="Display order in the response")
    is_active  = models.BooleanField(default=True,
                     help_text="Inactive parameters are excluded from responses")

    class Meta:
        ordering = ['order']

    def __str__(self):
        tier = "FREE" if self.is_free else "PAID"
        return f"[{tier}] {self.label} ({self.key})"


class FeatureFlag(models.Model):
    """
    Admin controls global platform settings.
    Only one row should exist — use the singleton pattern.
    """
    initial_free_credits    = models.PositiveIntegerField(default=5,
                                 help_text="Free credits given to every new user on registration")
    paid_credit_price_usd   = models.DecimalField(max_digits=6, decimal_places=2, default=1.00,
                                 help_text="Price in USD per paid credit")
    credits_per_purchase    = models.PositiveIntegerField(default=10,
                                 help_text="How many paid credits the user gets per purchase")
    updated_at              = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Feature Flag"

    def __str__(self):
        return f"Platform config (free credits: {self.initial_free_credits}, price: ${self.paid_credit_price_usd})"

    @classmethod
    def get(cls):
        """Always returns the single config row, creating it if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class UserPlan(models.Model):
    """
    Credit wallet for each user.
    free_credits  — given on registration, unlocks free parameters only
    paid_credits  — purchased, unlocks all parameters
    Checks consume paid_credits first, then free_credits.
    """
    user          = models.OneToOneField(User, on_delete=models.CASCADE, related_name='plan')
    free_credits  = models.PositiveIntegerField(default=0)
    paid_credits  = models.PositiveIntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} — free: {self.free_credits}, paid: {self.paid_credits}"

    @property
    def total_credits(self):
        return self.free_credits + self.paid_credits

    @property
    def is_paid_session(self):
        """True if the next check will use a paid credit."""
        return self.paid_credits > 0

    def consume_credit(self):
        """
        Deduct one credit. Paid credits are consumed first.
        Returns 'paid' or 'free' to indicate which was used.
        Raises ValueError if no credits remain.
        """
        if self.paid_credits > 0:
            self.paid_credits -= 1
            self.save(update_fields=['paid_credits', 'updated_at'])
            return 'paid'
        elif self.free_credits > 0:
            self.free_credits -= 1
            self.save(update_fields=['free_credits', 'updated_at'])
            return 'free'
        else:
            raise ValueError("No credits remaining")

    def add_paid_credits(self, amount):
        self.paid_credits += amount
        self.save(update_fields=['paid_credits', 'updated_at'])


class PaymentRecord(models.Model):
    """
    Logs every credit purchase. One-time payment per transaction.
    In production, store the payment gateway reference here.
    """
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    user              = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    amount_usd        = models.DecimalField(max_digits=8, decimal_places=2)
    credits_purchased = models.PositiveIntegerField()
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=255, blank=True,
                            help_text="Payment gateway transaction ID e.g. Stripe charge ID")
    created_at        = models.DateTimeField(auto_now_add=True)
    completed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — ${self.amount_usd} — {self.status}"
    