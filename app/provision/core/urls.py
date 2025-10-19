from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Devices CRUD
    path("", views.DeviceListView.as_view(), name="device_list"),
    path("devices/", views.DeviceListView.as_view(), name="device_list"),
    path("devices/create/", views.DeviceCreateView.as_view(), name="device_create"),
    path("devices/<int:pk>/", views.DeviceDetailView.as_view(), name="device_detail"),
    path("devices/<int:pk>/edit/", views.DeviceUpdateView.as_view(), name="device_update"),
    path("devices/<int:pk>/delete/", views.DeviceDeleteView.as_view(), name="device_delete"),

    # Profiles (master) — master/detail pages and CRUD for profiles
    path("profiles/", views.profile_list, name="profile_list"),
    path("profiles/create/", views.profile_create_or_update, name="profile_create"),
    path("profiles/<int:pk>/", views.profile_detail, name="profile_detail"),
    path("profiles/<int:pk>/edit/", views.profile_create_or_update, name="profile_edit"),
]