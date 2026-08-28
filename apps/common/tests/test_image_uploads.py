import base64
import io

import pytest
from django.core.files.base import ContentFile
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CustomUser


def png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def png_b64(data_uri: bool = False) -> str:
    raw = base64.b64encode(png_bytes()).decode()
    return f"data:image/png;base64,{raw}" if data_uri else raw


def make_user(email: str) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password="password123",
        role="CUSTOMER",
        phone=email[-10:],
    )


@pytest.mark.django_db
class TestBase64ImageUploads:
    """Images are stored as Django ImageFields via base64 JSON payloads."""

    def setup_method(self):
        self.client = APIClient()
        self.url = "/api/auth/me/"

    def test_patch_me_stores_uploaded_image(self):
        user = make_user("img1@example.com")
        self.client.force_authenticate(user=user)

        res = self.client.patch(self.url, {"profile_picture": png_b64()}, format="json")
        assert res.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.profile_picture
        assert user.profile_picture.name.startswith("profile_pictures/")
        assert user.profile_picture.name.endswith(".png")
        # The file really landed on storage and is servable.
        with user.profile_picture.open() as fh:
            assert fh.read(8) == b"\x89PNG\r\n\x1a\n"
        assert res.data["profile_picture"].startswith("http")

    def test_patch_me_accepts_data_uri(self):
        user = make_user("img2@example.com")
        self.client.force_authenticate(user=user)

        res = self.client.patch(
            self.url, {"profile_picture": png_b64(data_uri=True)}, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.profile_picture

    def test_rejects_non_image_payload(self):
        user = make_user("img3@example.com")
        self.client.force_authenticate(user=user)

        junk = base64.b64encode(b"definitely not an image").decode()
        res = self.client.patch(self.url, {"profile_picture": junk}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        user.refresh_from_db()
        assert not user.profile_picture

    def test_null_clears_existing_image(self):
        user = make_user("img4@example.com")
        user.profile_picture.save(
            "seed.png", ContentFile(png_bytes()), save=True
        )
        self.client.force_authenticate(user=user)

        res = self.client.patch(self.url, {"profile_picture": None}, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["profile_picture"] is None
        user.refresh_from_db()
        assert not user.profile_picture