"""Auth backend for `app_user` (email login, password_hash column)."""

from __future__ import annotations

from django.contrib.auth.backends import ModelBackend

from .models import AppUser


class AppUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email") or username
        if email is None or password is None:
            return None
        try:
            user = AppUser.objects.get(email__iexact=email)
        except AppUser.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return AppUser.objects.get(pk=user_id)
        except AppUser.DoesNotExist:
            return None
