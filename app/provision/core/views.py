from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import DeviceConfig, DeviceProfile
from .forms import DeviceProfileForm, DeviceFormSet
from django.http import Http404

# helper decorator for staff-only views
staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)


# Device CRUD views (simplified; reuse existing patterns)
class DeviceListView(LoginRequiredMixin, ListView):
    template_name = "core/device_list.html"
    context_object_name = "devices"
    paginate_by = 25

    def get_queryset(self):
        qs = DeviceConfig.objects.select_related("profile").all().order_by("id")
        q = self.request.GET.get("q")
        if q:
            from django.db.models import Q
            qs = qs.filter(Q(identifier__icontains=q) | Q(mac_address__icontains=q) | Q(display_name__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


class DeviceCreateView(LoginRequiredMixin, CreateView):
    model = DeviceConfig
    template_name = "core/device_form.html"
    fields = ["profile", "identifier", "mac_address", "display_name", "user_register", "passwd_register", "ip_address", "public_ip", "private_ip"]
    success_url = reverse_lazy("core:device_list")

    def form_valid(self, form):
        messages.success(self.request, "Dispositivo criado com sucesso.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erros foram encontrados no formulário.")
        return super().form_invalid(form)


class DeviceUpdateView(LoginRequiredMixin, UpdateView):
    model = DeviceConfig
    template_name = "core/device_form.html"
    fields = ["profile", "identifier", "mac_address", "display_name", "user_register", "passwd_register", "ip_address", "public_ip", "private_ip"]
    success_url = reverse_lazy("core:device_list")

    def form_valid(self, form):
        messages.success(self.request, "Dispositivo atualizado com sucesso.")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erros foram encontrados no formulário.")
        return super().form_invalid(form)


class DeviceDetailView(LoginRequiredMixin, DetailView):
    """
    Detail view for DeviceConfig with optimized provisioning prefetch.
    """
    model = DeviceConfig
    template_name = "core/device_detail.html"
    context_object_name = "device"

    def get_queryset(self):
        # select_related profile to avoid an extra query when accessing device.profile in template
        return DeviceConfig.objects.select_related("profile")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        device = self.get_object()

        # lazy import to avoid circular import issues
        try:
            from .models import Provisioning
        except Exception:
            Provisioning = None

        if Provisioning:
            prov_qs = Provisioning.objects.filter(device=device).order_by("-created_at")
            try:
                setattr(device, "provisionings", prov_qs)
            except Exception:
                logger = __import__("logging").getLogger(__name__)
                logger.exception("Failed to attach provisionings queryset to device instance")

            ctx["recent_provisionings"] = prov_qs[:20]
            try:
                ctx["provisionings_count"] = prov_qs.count()
            except Exception:
                ctx["provisionings_count"] = None
        else:
            ctx["recent_provisionings"] = []
            ctx["provisionings_count"] = 0

        return ctx


class DeviceDeleteView(LoginRequiredMixin, DeleteView):
    model = DeviceConfig
    template_name = "core/device_confirm_delete.html"
    success_url = reverse_lazy("core:device_list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Dispositivo removido com sucesso.")
        return super().delete(request, *args, **kwargs)


# Profile (master) + Device (detail) master/detail view using inline formset
@login_required
def profile_list(request):
    profiles = DeviceProfile.objects.all().order_by("name")
    return render(request, "core/profile_list.html", {"profiles": profiles})


@login_required
def profile_detail(request, pk):
    profile = get_object_or_404(DeviceProfile, pk=pk)
    devices = profile.devices.all().order_by("identifier")
    return render(request, "core/profile_detail.html", {"profile": profile, "devices": devices})


# require staff for create/edit profile
@login_required
@staff_required
def profile_create_or_update(request, pk=None):
    if pk:
        profile = get_object_or_404(DeviceProfile, pk=pk)
    else:
        profile = DeviceProfile()

    if request.method == "POST":
        form = DeviceProfileForm(request.POST, instance=profile)
        formset = DeviceFormSet(request.POST, instance=profile)
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    profile = form.save()
                    formset.instance = profile
                    formset.save()
                messages.success(request, "Perfil e dispositivos salvos com sucesso.")
                return redirect("core:profile_detail", pk=profile.pk)
            except Exception:
                messages.exception(request, "Falha ao salvar perfil e dispositivos.")
        else:
            messages.error(request, "Erros no formulário. Corrija e tente novamente.")
    else:
        form = DeviceProfileForm(instance=profile)
        formset = DeviceFormSet(instance=profile)

    return render(request, "core/profile_form.html", {"form": form, "formset": formset, "profile": profile})