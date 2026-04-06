from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LogoutView, ChangePasswordView,
    UserProfileViewSet, PrivatePersonViewSet,
    CompatibilityViewSet, PlanViewSet,
)

router = DefaultRouter()
router.register(r'profiles',        UserProfileViewSet,   basename='profile')
router.register(r'private-persons', PrivatePersonViewSet, basename='private-person')
router.register(r'compatibility',   CompatibilityViewSet, basename='compatibility')
router.register(r'plan',            PlanViewSet,          basename='plan')

urlpatterns = [
    path('auth/register/',        RegisterView.as_view(),       name='register'),
    path('auth/logout/',          LogoutView.as_view(),         name='logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('', include(router.urls)),
]