from django.urls import re_path
from .views import download_config

urlpatterns = [
    re_path(r'^download-xml(?:/(?P<filename>[^/]+))?/$', download_config, name='download-xml'),
    path("whoami/", oauth_views.whoami, name="whoami"),
]