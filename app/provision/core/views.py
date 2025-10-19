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
from django.views.decorators.http import require_http_methods
from django.conf import settings
from datetime import datetime
from django.core.paginator import Paginator
import xml.etree.ElementTree as ET
import logging
import os
import re

# Use the shared mongo util
from api.utils.mongo import get_mongo_client

logger = logging.getLogger(__name__)

# helper decorator for staff-only views
staff_required = user_passes_test(lambda u: u.is_active and u.is_staff)

# --- helper local para sanitizar nome de arquivo ---
def _sanitize_filename(name: str) -> str:
    if not name:
        return "template"
    # remove caminhos e caracteres inválidos
    base = os.path.basename(name)
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', base)
    if len(safe) > 120:
        safe = safe[:120]
    if not safe:
        safe = "template"
    return safe

# View to list templates imported
# -- template_download: ler 'template' com fallback para 'content' --
@require_http_methods(["GET"])
@login_required
def template_download(request, name: str):
    try:
        db = get_mongo_client()
        coll = getattr(db, "device_templates", db.get_collection("device_templates"))
    except Exception as exc:
        logger.exception("Falha ao conectar ao MongoDB: %s", exc)
        raise Http404("Template não encontrado.")

    try:
        doc = coll.find_one({"_id": name})
    except Exception as exc:
        logger.exception("Erro ao consultar template %s: %s", name, exc)
        raise Http404("Template não encontrado.")

    if not doc:
        raise Http404("Template não encontrado.")

    # prefer 'template' com fallback para 'content'
    content = doc.get("template") or doc.get("content") or ""
    if isinstance(content, str):
        body = content.encode("utf-8")
    else:
        body = content

    file_type = (doc.get("file_type") or "").lower()
    filename = doc.get("filename") or f"{name}.{file_type or 'txt'}"
    filename = _sanitize_filename(filename)

    if file_type == "xml":
        content_type = "application/xml; charset=utf-8"
    else:
        content_type = "text/plain; charset=utf-8"

    resp = HttpResponse(body, content_type=content_type)
    resp["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

# --- view de remoção ---
@require_http_methods(["POST"])
@login_required
def template_delete(request, name: str):
    """
    Remove documento do MongoDB (collection device_templates) com _id == name.
    Requer POST (form com CSRF token).
    """
    try:
        db = get_mongo_client()
        coll = getattr(db, "device_templates", db.get_collection("device_templates"))
    except Exception as exc:
        logger.exception("Falha ao conectar ao MongoDB para deletar %s: %s", name, exc)
        # redirecionar para a lista com mensagem de erro via messages (se preferir)
        from django.contrib import messages
        messages.error(request, "Falha ao conectar ao MongoDB para deletar o template.")
        return redirect("core:template_list")

    try:
        result = coll.delete_one({"_id": name})
    except Exception as exc:
        logger.exception("Erro ao deletar template %s: %s", name, exc)
        from django.contrib import messages
        messages.error(request, "Erro ao remover o template. Verifique os logs.")
        return redirect("core:template_list")

    from django.contrib import messages
    if result.deleted_count:
        messages.success(request, f"Template '{name}' removido com sucesso.")
    else:
        messages.warning(request, f"Template '{name}' não encontrado.")
    return redirect("core:template_list")
    
# -- template_list: converte _id para id e mantém compatibilidade de campo template/content --
@login_required
def template_list(request):
    q = (request.GET.get("q") or "").strip()
    page = request.GET.get("page", 1)

    try:
        db = get_mongo_client()
        coll = getattr(db, "device_templates", db.get_collection("device_templates"))
    except Exception as exc:
        messages.error(request, "Não foi possível conectar ao MongoDB. Verifique a configuração.")
        context = {"page_obj": None, "q": q}
        return render(request, "core/template_list.html", context)

    query = {}
    if q:
        query = {"_id": {"$regex": q, "$options": "i"}}

    try:
        # não traz o campo template para agilizar a listagem
        cursor = coll.find(query, projection={"template": 0, "content": 0}).sort("uploaded_at", -1)
        docs = []
        for d in cursor:
            d["id"] = str(d.get("_id"))
            docs.append(d)
    except Exception as exc:
        logger.exception("Erro ao consultar templates: %s", exc)
        messages.error(request, "Erro ao consultar templates no MongoDB.")
        docs = []

    paginator = Paginator(docs, 25)
    try:
        page_obj = paginator.get_page(page)
    except Exception:
        page_obj = paginator.get_page(1)

    context = {"page_obj": page_obj, "q": q}
    return render(request, "core/template_list.html", context)

# -- template_detail: usar 'template' com fallback em 'content' --
@login_required
def template_detail(request, name: str):
    try:
        db = get_mongo_client()
        coll = getattr(db, "device_templates", db.get_collection("device_templates"))
    except Exception as exc:
        logger.exception("Falha ao obter conexão com MongoDB: %s", exc)
        raise Http404("Template não encontrado.")

    try:
        doc = coll.find_one({"_id": name})
    except Exception as exc:
        logger.exception("Erro ao consultar device_templates para _id=%s: %s", name, exc)
        raise Http404("Template não encontrado.")

    if not doc:
        raise Http404("Template não encontrado.")

    # adicionar id para o template acessar sem underscore
    doc["id"] = str(doc.get("_id"))

    # prefer 'template' (schema API) e cair em 'content' como fallback
    content = doc.get("template") or doc.get("content") or ""

    context = {"doc": doc, "content": content}
    return render(request, "core/template_detail.html", context)

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

# -- import_template: salvar 'template' (compatível com api.views) --
@require_http_methods(["GET", "POST"])
@login_required
def import_template(request):
    """
    Upload de arquivo .xml ou .cfg e salvamento no MongoDB.
    Usa api.utils.mongo.get_mongo_client() para obter o DB e grava em collection device_templates.
    O campo 'name' é usado como chave (_id).
    """
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        uploaded = request.FILES.get("file")
        overwrite = request.POST.get("overwrite") in ("on", "true", "1")

        if not name:
            messages.error(request, "Informe um nome para o template.")
            return render(request, "core/import_template.html", {"name": name})

        if not uploaded:
            messages.error(request, "Selecione um arquivo (.xml ou .cfg).")
            return render(request, "core/import_template.html", {"name": name})

        _, ext = os.path.splitext(uploaded.name.lower())
        if ext not in (".xml", ".cfg"):
            messages.error(request, "Extensão inválida. Apenas .xml e .cfg são permitidos.")
            return render(request, "core/import_template.html", {"name": name})

        raw = uploaded.read()
        try:
            content = raw.decode("utf-8")
        except Exception:
            content = raw.decode("latin-1", errors="replace")

        file_type = "xml" if ext == ".xml" else "cfg"

        # validação adicional para XML
        if file_type == "xml":
            try:
                ET.fromstring(content)
            except ET.ParseError as exc:
                messages.error(request, f"XML inválido: {exc}")
                return render(request, "core/import_template.html", {"name": name})

        # obtém DB via utilitário centralizado
        try:
            db = get_mongo_client()
            coll = getattr(db, "device_templates", db.get_collection("device_templates"))
        except Exception as exc:
            messages.error(request, "Falha ao conectar ao MongoDB. Verifique logs.")
            return render(request, "core/import_template.html", {"name": name})

        existing = coll.find_one({"_id": name})
        if existing and not overwrite:
            messages.error(request, "Já existe um template com esse nome. Marque 'Sobrescrever' para atualizar.")
            return render(request, "core/import_template.html", {"name": name})

        # Usar chave 'template' para compatibilidade com app/provision/api/views.py
        doc = {
            "_id": name,
            "filename": uploaded.name,
            "file_type": file_type,
            "template": content,      # chave esperada pela API
            "content": content,       # manter como fallback/compatibilidade (opcional)
            "uploaded_by": request.user.username if request.user.is_authenticated else None,
            "uploaded_at": datetime.utcnow(),
        }

        try:
            coll.replace_one({"_id": name}, doc, upsert=True)
        except Exception:
            messages.error(request, "Falha ao salvar o template no MongoDB. Verifique logs.")
            return render(request, "core/import_template.html", {"name": name})

        messages.success(request, f"Template '{name}' salvo com sucesso.")
        return redirect("core:template_list")
    else:
        return render(request, "core/import_template.html", {})