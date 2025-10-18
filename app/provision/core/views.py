from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse, Http404
from django.utils.encoding import smart_str
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.models import User
import csv
import logging

logger = logging.getLogger(__name__)


class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff


# Device views
class DeviceListView(LoginRequiredMixin, ListView):
    """
    List view for DeviceConfig. Supports simple search via ?q= over identifier and model.
    """
    template_name = "core/device_list.html"
    context_object_name = "devices"
    paginate_by = 25

    def get_queryset(self):
        # import lazily to avoid errors if models are not yet available
        try:
            from .models import DeviceConfig
        except Exception as exc:
            logger.exception("DeviceListView: failed to import DeviceConfig: %s", exc)
            # return empty queryset-like list
            return DeviceConfig.objects.none() if 'DeviceConfig' in globals() else []
        qs = DeviceConfig.objects.all().order_by('id')
        q = self.request.GET.get('q')
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(identifier__icontains=q) | Q(model__icontains=q) | Q(mac_address__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        return ctx


class DeviceCreateView(LoginRequiredMixin, CreateView):
    """
    Create view for DeviceConfig. Uses a lazy ModelForm factory so the model can be created later.
    """
    template_name = "core/device_form.html"
    success_url = reverse_lazy('core:device_list')

    def get_form_class(self):
        from .forms import get_device_form
        return get_device_form()

    def form_valid(self, form):
        messages.success(self.request, "Dispositivo criado com sucesso.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erros foram encontrados no formulário.")
        return super().form_invalid(form)


class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update view for DeviceConfig.
    """
    template_name = "core/device_form.html"
    success_url = reverse_lazy('core:device_list')

    def get_form_class(self):
        from .forms import get_device_form
        return get_device_form()

    def get_object(self, queryset=None):
        from .models import DeviceConfig
        pk = self.kwargs.get('pk')
        return get_object_or_404(DeviceConfig, pk=pk)

    def form_valid(self, form):
        messages.success(self.request, "Dispositivo atualizado com sucesso.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erros foram encontrados no formulário.")
        return super().form_invalid(form)


class DeviceDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for DeviceConfig.
    """
    template_name = "core/device_detail.html"
    context_object_name = "device"

    def get_object(self, queryset=None):
        from .models import DeviceConfig
        pk = self.kwargs.get('pk')
        return get_object_or_404(DeviceConfig, pk=pk)


class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    """
    Delete confirmation view for DeviceConfig.
    """
    template_name = "core/device_confirm_delete.html"
    success_url = reverse_lazy('core:device_list')

    def get_object(self, queryset=None):
        from .models import DeviceConfig
        pk = self.kwargs.get('pk')
        return get_object_or_404(DeviceConfig, pk=pk)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Dispositivo removido com sucesso.")
        return super().delete(request, *args, **kwargs)


@login_required
def export_devices_csv(request):
    """
    Export all devices as CSV. Columns taken from model._meta.fields for flexibility.
    """
    try:
        from .models import DeviceConfig
    except Exception as exc:
        logger.exception("export_devices_csv: DeviceConfig import failed: %s", exc)
        raise Http404("Modelo DeviceConfig não encontrado")

    qs = DeviceConfig.objects.all().order_by('id')

    # Prepare CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="devices.csv"'

    writer = csv.writer(response)
    field_objs = [f for f in DeviceConfig._meta.fields]
    headers = [f.name for f in field_objs]
    writer.writerow(headers)

    for obj in qs:
        row = []
        for f in field_objs:
            val = getattr(obj, f.name)
            row.append(smart_str(val))
        writer.writerow(row)

    return response


# User management view
class UserCreateView(LoginRequiredMixin, StaffRequiredMixin, CreateView):
    """
    Page to create users through the app. Only staff users can access this view.
    This complements the admin interface.
    """
    model = User
    form_class = UserCreationForm
    template_name = "core/user_create.html"
    success_url = reverse_lazy('core:device_list')

    def form_valid(self, form):
        resp = super().form_valid(form)
        messages.success(self.request, "Usuário criado com sucesso. Configure permissões no Admin se necessário.")
        return resp