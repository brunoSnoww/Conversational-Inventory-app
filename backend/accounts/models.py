"""Maps to Goose-managed `app_user` table."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models


class AppUserManager(BaseUserManager):
    def create_user(self, email: str, password: str | None = None) -> "AppUser":
        from django.contrib.auth.hashers import make_password
        from django.db import connection

        if not email:
            raise ValueError("email required")
        email = self.normalize_email(email)
        hashed = make_password(password)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO app_user (email, password_hash)
                VALUES (%s, %s)
                RETURNING user_id, email, is_active, created_at, updated_at
                """,
                [email, hashed],
            )
            row = cursor.fetchone()
        assert row is not None
        user = self.model(
            user_id=row[0],
            email=row[1],
            is_active=row[2],
            created_at=row[3],
            updated_at=row[4],
        )
        user.password = hashed
        return user


class AppUser(AbstractBaseUser):
    # Goose-managed table has no last_login column.
    last_login = None

    user_id = models.BigIntegerField(primary_key=True)
    email = models.EmailField(max_length=320, unique=True)
    password = models.CharField(max_length=128, db_column="password_hash")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    objects = AppUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        managed = False
        db_table = "app_user"

    def __str__(self) -> str:
        return self.email

    @property
    def pk(self) -> int:
        return self.user_id

    @property
    def id(self) -> int:
        return self.user_id
