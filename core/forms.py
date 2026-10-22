"""
core/forms.py — Forms for image upload validation.
"""

import os

from django import forms

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_UPLOAD_MB = 10


class VehicleImageUploadForm(forms.Form):
    """Handles both file-upload and base64/camera-blob paths."""

    image = forms.ImageField(
        required=False,
        help_text="Upload a vehicle image (JPG or PNG, max 10 MB).",
    )
    # For camera-captured base64 data
    image_data = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Base64-encoded image from camera capture.",
    )

    def clean(self):
        cleaned = super().clean()
        image = cleaned.get("image")
        image_data = cleaned.get("image_data", "").strip()

        if not image and not image_data:
            raise forms.ValidationError("Please upload an image file or capture one with the camera.")

        if image:
            # Validate extension
            ext = os.path.splitext(image.name)[1].lstrip(".").lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise forms.ValidationError(f"Only {', '.join(ALLOWED_EXTENSIONS)} files are allowed.")

            # Validate size
            if image.size > MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f"File size must be under {MAX_UPLOAD_MB} MB.")

        return cleaned
