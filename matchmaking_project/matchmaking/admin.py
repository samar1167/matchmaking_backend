from django.contrib import admin
from .models import (
    UserProfile, UserMatchPreference, UserMatch, UserConnection, PrivatePerson, CompatibilityScore,
    CompatibilityTransaction, CompatibilityParameter, FeatureFlag, UserPlan,
    PaymentRecord, AuthActionToken, ChatConversation, ChatMessage,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'user_first_name', 'user_last_name', 'gender', 'date_of_birth', 'place_of_birth', 'public_match', 'created_at')
    list_filter = ('gender', 'public_match')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'place_of_birth')

    def user_first_name(self, obj):
        return obj.user.first_name

    def user_last_name(self, obj):
        return obj.user.last_name


@admin.register(UserMatchPreference)
class UserMatchPreferenceAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'preferred_gender',
        'preferred_age_min',
        'preferred_age_max',
        'preferred_relationship_intent',
        'updated_at',
    )
    list_filter = ('preferred_gender', 'preferred_relationship_intent', 'preferred_marital_status')
    search_fields = (
        'user__email',
    )


@admin.register(UserMatch)
class UserMatchAdmin(admin.ModelAdmin):
    list_display = ('user', 'matched_user', 'score', 'rank', 'created_at')
    list_filter = ('rank',)
    search_fields = ('user__user__email', 'matched_user__user__email')
    ordering = ('rank', '-score')
    list_select_related = ('user__user', 'matched_user__user')


@admin.register(UserConnection)
class UserConnectionAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'receiver', 'status', 'requested_at', 'responded_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('requester__user__email', 'receiver__user__email')
    ordering = ('-updated_at',)
    readonly_fields = ('profile_low', 'profile_high', 'requested_at', 'responded_at', 'updated_at')
    list_select_related = ('requester__user', 'receiver__user', 'profile_low__user', 'profile_high__user')


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'connection', 'user_a', 'user_b', 'last_message_at', 'user_a_unread_count', 'user_b_unread_count')
    search_fields = ('user_a__user__email', 'user_b__user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_select_related = ('connection', 'user_a__user', 'user_b__user')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'sender', 'receiver', 'created_at', 'deleted_at')
    search_fields = ('sender__user__email', 'receiver__user__email', 'body', 'client_message_id')
    readonly_fields = ('conversation', 'sender', 'receiver', 'body', 'client_message_id', 'created_at', 'deleted_at')
    list_select_related = ('conversation', 'sender__user', 'receiver__user')


@admin.register(PrivatePerson)
class PrivatePersonAdmin(admin.ModelAdmin):
    list_display  = ('name', 'owner', 'date_of_birth', 'created_at')
    search_fields = ('name', 'owner__username')


@admin.register(CompatibilityScore)
class CompatibilityScoreAdmin(admin.ModelAdmin):
    list_display  = ('user', 'user_name', 'matched_user_name', 'matched_user_is_private', 'overall_score', 'is_paid', 'created_at')
    ordering      = ('-overall_score',)
    list_select_related = (
        'user__user',
        'matched_user__user',
        'matched_private_person',
    )

    @admin.display(description='User name', ordering='user__user__first_name')
    def user_name(self, obj):
        return self._user_display_name(obj.user.user)

    @admin.display(description='Matched user name')
    def matched_user_name(self, obj):
        if obj.matched_user_id:
            return self._user_display_name(obj.matched_user.user)
        if obj.matched_private_person_id:
            return obj.matched_private_person.name
        return '-'

    @admin.display(description='Matched user private', boolean=True)
    def matched_user_is_private(self, obj):
        return obj.matched_private_person_id is not None

    def _user_display_name(self, user):
        full_name = user.get_full_name()
        return full_name or user.username or user.email


@admin.register(CompatibilityTransaction)
class CompatibilityTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'matched_user_name',
        'matched_user_is_private',
        'credit_type',
        'overall_score',
        'credits_remaining_after',
        'created_at',
    )
    list_filter = ('credit_type', 'is_paid')
    search_fields = ('user__user__email', 'user__user__username', 'matched_private_person__name')
    readonly_fields = (
        'user',
        'matched_user',
        'matched_private_person',
        'compatibility_score',
        'credit_type',
        'is_paid',
        'overall_score',
        'credits_remaining_after',
        'description',
        'api_response',
        'created_at',
    )
    ordering = ('-created_at',)
    list_select_related = (
        'user__user',
        'matched_user__user',
        'matched_private_person',
        'compatibility_score',
    )

    @admin.display(description='Matched user name')
    def matched_user_name(self, obj):
        if obj.matched_user_id:
            return self._user_display_name(obj.matched_user.user)
        if obj.matched_private_person_id:
            return obj.matched_private_person.name
        return '-'

    @admin.display(description='Matched user private', boolean=True)
    def matched_user_is_private(self, obj):
        return obj.matched_private_person_id is not None

    def _user_display_name(self, user):
        full_name = user.get_full_name()
        return full_name or user.username or user.email


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


@admin.register(AuthActionToken)
class AuthActionTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'purpose', 'expires_at', 'used_at', 'created_at')
    list_filter = ('purpose',)
    search_fields = ('user__email', 'token')
    readonly_fields = ('user', 'purpose', 'token', 'expires_at', 'used_at', 'created_at')
