from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.DeviceListView.as_view(), name='device_list'),
    path('create/', views.DeviceCreateView.as_view(), name='device_create'),
    path('<int:pk>/', views.DeviceDetailView.as_view(), name='device_detail'),
    path('<int:pk>/edit/', views.DeviceUpdateView.as_view(), name='device_update'),
    path('<int:pk>/delete/', views.DeviceDeleteView.as_view(), name='device_delete'),
    path('export/csv/', views.export_devices_csv, name='device_export_csv'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
]