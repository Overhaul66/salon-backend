"""
Shared DRF fields.

``Base64ImageField`` lets clients send images as base64 strings inside normal
JSON payloads (or ``null`` to clear). This avoids React Native multipart
entirely - RN's native multipart file streaming silently corrupts binary parts,
while a base64 *string* travels through JSON intact.
"""

import base64
import binascii
import io
import re
import uuid

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

# Matches ``data:image/jpeg;base64,<payload>`` (prefix is optional).
_DATA_URI_RE = re.compile(r"^data:(?P<mime>[\w./+-]+);base64,", re.IGNORECASE)

default_error_messages = {
    "invalid": "A valid image was not submitted.",
    "too_large": "Image exceeds the maximum allowed size.",
}


class Base64ImageField(serializers.Field):
    """
    Accepts ``None``, ``""``, raw base64 or a data-URI string and produces a
    ``ContentFile`` suitable for direct assignment to an ``ImageField``.

    On read it returns an absolute URL so React Native's ``<Image>`` can render
    it without any path juggling.
    """

    default_error_messages = default_error_messages

    def __init__(self, **kwargs):
        self.max_bytes = int(getattr(settings, "IMAGE_MAX_BYTES", 10 * 1024 * 1024))
        kwargs.setdefault("allow_null", True)
        if "required" not in kwargs:
            kwargs["required"] = False
        super().__init__(**kwargs)

    def _extension_for(self, pil_image) -> str:
        fmt = (pil_image.format or "").lower()
        return {
            "jpeg": "jpg",
            "jpg": "jpg",
            "png": "png",
            "gif": "gif",
            "webp": "webp",
        }.get(fmt, "jpg")

    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        if not isinstance(data, str):
            self.fail("invalid")

        raw = _DATA_URI_RE.sub("", data.strip())
        try:
            decoded = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            self.fail("invalid")

        if len(decoded) > self.max_bytes:
            self.fail("too_large")

        # Validate that the bytes really are an image (also sniffs format).
        try:
            with Image.open(io.BytesIO(decoded)) as img:
                img.verify()
            with Image.open(io.BytesIO(decoded)) as img:
                extension = self._extension_for(img)
        except UnidentifiedImageError:
            self.fail("invalid")

        return ContentFile(
            decoded,
            name=f"{uuid.uuid4().hex}.{extension}",
        )

    def to_representation(self, value):
        if not value:
            return None
        request = self.context.get("request")
        url = value.url
        if request is not None and not url.startswith(("http://", "https://")):
            return request.build_absolute_uri(url)
        return url
