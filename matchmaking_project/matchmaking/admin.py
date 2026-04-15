from django.contrib import admin
from .models import (
    UserProfile, PrivatePerson, CompatibilityScore,
    CompatibilityParameter, FeatureFlag, UserPlan, PaymentRecord,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'user_first_name', 'user_last_name', 'date_of_birth', 'place_of_birth', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'place_of_birth')

    def user_first_name(self, obj):
        return obj.user.first_name

    def user_last_name(self, obj):
        return obj.user.last_name


@admin.register(PrivatePerson)
class PrivatePersonAdmin(admin.ModelAdmin):
    list_display  = ('name', 'owner', 'date_of_birth', 'created_at')
    search_fields = ('name', 'owner__username')


@admin.register(CompatibilityScore)
class CompatibilityScoreAdmin(admin.ModelAdmin):
    list_display  = ('user', 'overall_score', 'is_paid', 'is_private_match', 'created_at')
    ordering      = ('-overall_score',)


@admin.register(CompatibilityParameter)
class CompatibilityParameterAdmin(admin.ModelAdmin):
    list_display       = ('id', 'order', 'label', 'key', 'is_free', 'is_active')
    list_display_links = ('id', 'label')   # these become the clickable links
    list_editable      = ('is_free', 'is_active', 'order')
    ordering           = ('order',)
    # ↑ Admin can toggle free/paid directly from the list view


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = ('initial_free_credits', 'paid_credit_price_usd', 'credits_per_purchase', 'updated_at')

    def has_add_permission(self, request):
        # Only one row allowed — disable Add button if row exists
        return not FeatureFlag.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # Never delete the config row


@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display  = ('user', 'free_credits', 'paid_credits', 'updated_at')
    search_fields = ('user__email',)
    list_editable = ('free_credits', 'paid_credits')
    # ↑ Admin can manually adjust credits for any user


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display  = ('user', 'amount_usd', 'credits_purchased', 'status', 'payment_reference', 'created_at')
    list_filter   = ('status',)
    search_fields = ('user__email', 'payment_reference')
    readonly_fields = ('user', 'amount_usd', 'credits_purchased', 'created_at', 'completed_at')
