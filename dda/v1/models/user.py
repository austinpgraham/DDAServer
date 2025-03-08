import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from enum import Enum
from django.db import models
from django.conf import settings
from dda.v1.models.base import AbstractDatedModel


class UserSource(Enum):
    GOOGLE = "google"


class User(AbstractDatedModel):
    """
    A user in the DDA system, having been sourced by an OAuth provider.

    Attributes:
        email (str): The user's email.
        family_name (str): The user's surname.
        given_name (str): The user's first name.
        id (UUID): A unique ID assigned by our system. Auto-generated on create.
        is_email_verified (bool): Has the user verified their email?
        phone_number (str): The user's phone number in E.164 format.
        profile_picture (str): A link to the user's profile photo, if present.
        source (str): Where the original user signup came from.
    """
    email = models.CharField(null=False)
    family_name = models.CharField(null=False)
    given_name = models.CharField(null=False)
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    is_email_verified = models.BooleanField(default=False)
    phone_number = models.CharField()
    profile_picture = models.CharField()
    source = models.CharField(
        choices=[(entry.name, entry.value) for entry in UserSource],
        null=False
    )

    def __str__(self) -> str:
        return f"{id}"


def _get_expiry_date() -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(minutes=settings.SESSION_LENGTH_MINUTES)


class SessionToken(models.Model):
    """
    A token that ties to a user and marks their session. Should be used
    as an authentication method for any API that requires fetching data.

    Attributes:
        token (str): The token identifying the session.
        expires_at (datetime): The time when this token expires.
        user (User): The user associated with this token.
    """
    token = models.CharField(null=False, primary_key=True)
    expires_at = models.DateField(default=_get_expiry_date, null=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE
    )

    @property
    def is_expired(self) -> bool:
        current_time = datetime.now(tz=timezone.utc)
        return current_time >= self.expires_at
