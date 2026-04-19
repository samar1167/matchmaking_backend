from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Matchmaking API",
        default_version='v1',
        description="Astrological matchmaking backend API",
        contact=openapi.Contact(email="admin@matchmaking.com"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
    authentication_classes=[], 
)

admin.site.site_header = "Luster Admin Console"
admin.site.site_title = "Luster Admin Console"
admin.site.index_title = "Luster Admin Console"

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT auth
    path('api/auth/refresh/', TokenRefreshView.as_view(),    name='token_refresh'),

    # App routes
    path('api/', include('matchmaking.urls')),

    # Swagger UI
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),

    # ReDoc (cleaner read-only docs)
    re_path(r'^redoc/$',   schema_view.with_ui('redoc',   cache_timeout=0), name='schema-redoc'),

    # Raw JSON schema
    re_path(r'^swagger.json$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
