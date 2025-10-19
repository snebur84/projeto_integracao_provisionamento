import pytest
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import DeviceProfile


@pytest.mark.django_db
def test_profile_list_requires_login(client):
    url = reverse("core:profile_list")
    resp = client.get(url)
    assert resp.status_code in (302, 301)  # redirect to login


@pytest.mark.django_db
def test_profile_list_shows_profiles(client, django_user_model):
    # create and login user
    user = django_user_model.objects.create_user("u1", password="pw")
    user.is_staff = True
    user.save()
    client.login(username="u1", password="pw")
    DeviceProfile.objects.create(name="ShowMe")
    resp = client.get(reverse("core:profile_list"))
    assert resp.status_code == 200
    assert b"ShowMe" in resp.content


@pytest.mark.django_db
def test_profile_create_or_update_post_creates_profile(client, django_user_model):
    user = django_user_model.objects.create_user("u2", password="pw")
    user.is_staff = True
    user.save()
    client.login(username="u2", password="pw")
    resp = client.post(reverse("core:profile_create"), data={"name": "NewProfile", "port_server": 5060, "protocol_type": "UDP"})
    # should redirect to detail on success
    assert resp.status_code in (302, 301)
    assert DeviceProfile.objects.filter(name="NewProfile").exists()