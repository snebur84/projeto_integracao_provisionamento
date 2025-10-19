from django.urls import path, re_path
from .views import download_config
from . import oauth_views

app_name = "api"

urlpatterns = [
    re_path(r'^download-xml(?:/(?P<filename>[^/]+))?/$', download_config, name='download-xml'),
    path('whoami/', oauth_views.whoami, name='whoami'),
]