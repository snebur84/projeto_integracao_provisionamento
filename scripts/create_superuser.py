#!/usr/bin/env python
import os
import sys

# Garantir que o diretório atual (onde o container foi iniciado / WORKDIR) esteja no sys.path
# Isso permite que o script seja executado a partir de /app/scripts enquanto o package Django
# (provision) permanece importável quando o projeto está em /app/app/provision.
sys.path.insert(0, os.getcwd())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "provision.settings_docker"))

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")

if not username or not password:
    print("DJANGO_SUPERUSER_USERNAME and/or DJANGO_SUPERUSER_PASSWORD not provided — skipping automatic superuser creation.")
else:
    if User.objects.filter(username=username).exists():
        print(f"Superuser '{username}' already exists — skipping creation.")
    else:
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"Superuser '{username}' created.")