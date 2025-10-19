from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI / Swagger (drf-spectacular)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # API endpoints
    path('api/', include('api.urls')),

    # OAuth2 endpoints (django-oauth-toolkit)
    # Exposes /o/authorize/, /o/token/, /o/revoke_token/, /o/introspect/, /o/applications/, etc.
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # Public login/logout (login page is a standalone template core/login.html)
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # Management interface for devices (core app) — namespace required for reverse lookups
    path('', include('core.urls', namespace='core')),
]