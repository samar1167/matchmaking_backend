from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView, ChangePasswordView,
    VerifyEmailView, ResendVerificationView, ForgotPasswordView, ResetPasswordView,
    UserProfileViewSet, UserMatchPreferenceViewSet, UserMatchViewSet, PrivatePersonViewSet,
    UserConnectionViewSet, CompatibilityViewSet, PlanViewSet,
)

router = DefaultRouter()
router.register(r'profiles',        UserProfileViewSet,   basename='profile')
router.register(r'match-preferences', UserMatchPreferenceViewSet, basename='match-preference')
router.register(r'user-matches',    UserMatchViewSet,     basename='user-match')
router.register(r'connections',     UserConnectionViewSet, basename='connection')
router.register(r'private-persons', PrivatePersonViewSet, basename='private-person')
router.register(r'compatibility',   CompatibilityViewSet, basename='compatibility')
router.register(r'plan',            PlanViewSet,          basename='plan')

urlpatterns = [
    path('auth/register/',        RegisterView.as_view(),       name='register'),
    path('auth/login/',           LoginView.as_view(),          name='login'),
    path('auth/logout/',          LogoutView.as_view(),         name='logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/verify-email/',    VerifyEmailView.as_view(),    name='verify-email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('auth/reset-password/',  ResetPasswordView.as_view(),  name='reset-password'),
    path('', include(router.urls)),
]
