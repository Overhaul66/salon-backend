# Image-specific serializer fields live in .fields (Base64ImageField).


class ImageKitReferenceField(serializers.CharField):
    """
    Serializes an `ImageKitFile` FK as its display URL on read, and accepts an
    ImageKit `file_id` on write. If the file was already registered and owned by
    the current user, it is reused. Otherwise the file is self-registered
    server-side: canonical metadata is fetched from ImageKit (never trusting the
    client), non-images and oversized files are rejected, and the record is
    created owned by `request.user` - so nobody can attach someone else's file
    to their salons/profiles.

    Subclassing ``CharField`` keeps OpenAPI generation clean (the wire format
    is a string file_id / URL).
    """

    default_error_messages = {
        "not_found": "This file is not registered or you do not own it.",
        "not_yours": "This file belongs to another user.",
        "invalid": "A valid file reference is required.",
    }

    def __init__(self, **kwargs):
        kwargs.setdefault("allow_null", True)
        if "required" not in kwargs:
            kwargs["required"] = False
        super().__init__(**kwargs)

    def to_representation(self, value):
        if value is None:
            return None
        return value.url

    def _fetch_and_register(self, file_id, owner):
        """Fetch canonical metadata from ImageKit and store it owned by `owner`."""
        try:
            details = fetch_file_details(file_id)
        except ImageKitError as exc:
            raise serializers.ValidationError({"file_id": exc.detail})

        mime_type = details.get("mime_type") or "unknown"
        if not str(mime_type).startswith("image/"):
            raise serializers.ValidationError(
                {
                    "file_id": (
                        "Only image files are supported "
                        f"(ImageKit detected: {mime_type}, "
                        f"{details.get('size', 0)} bytes)."
                    )
                }
            )

        size = int(details.get("size") or 0)
        if size > int(settings.IMAGEKIT_MAX_FILE_SIZE):
            raise serializers.ValidationError(
                {"file_id": "File exceeds the maximum allowed size."}
            )

        return ImageKitFile.objects.create(uploaded_by=owner, **details)

    def to_internal_value(self, data):
        if data is None or data == "":
            return None
        if not isinstance(data, str):
            raise serializers.ValidationError(self.error_messages["invalid"])

        request = self.context.get("request")
        user = getattr(request, "user", None)
        owner = (
            user
            if user is not None and getattr(user, "is_authenticated", False)
            else None
        )

        existing = ImageKitFile.objects.filter(file_id=data).first()
        if existing is not None:
            if owner is not None and existing.uploaded_by != owner:
                raise serializers.ValidationError(self.error_messages["not_yours"])
            return existing

        return self._fetch_and_register(data, owner)
