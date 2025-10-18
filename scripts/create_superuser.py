#!/usr/bin/env python
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", os.environ.get("DJANGO_SETTINGS_MODULE", "provision.settings_docker"))
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