from django.contrib import admin
from .models import UserProfile, PrivatePerson, CompatibilityScore

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'place_of_birth', 'created_at')
    search_fields = ('user__username', 'place_of_birth')

@admin.register(PrivatePerson)
class PrivatePersonAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'date_of_birth', 'place_of_birth', 'created_at')
    search_fields = ('name', 'owner__username')

@admin.register(CompatibilityScore)
class CompatibilityScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'overall_score', 'is_private_match', 'created_at')
    ordering = ('-overall_score',)
