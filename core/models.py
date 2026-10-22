"""
core/models.py

Database models for the Vehicle Damage & Insurance Claim app.

Cascade rules:
  - Deleting a User cascades to VehicleImage → DamageInsight → ClaimEstimate
    (handled via on_delete=CASCADE on each FK).

Indexes:
  - VehicleImage: user + uploaded_at
  - DamageInsight: vehicle_image
  - ClaimEstimate: damage_insight
"""

import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


# ──────────────────────────────────────────────────────────────────────────────
# Custom User
# ──────────────────────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    """Manager for the custom User model."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model.

    Email is the unique identifier (no username).
    Google OAuth fields (google_uid, avatar_url) are populated on first login
    via the allauth signal in core/signals.py.
    """

    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    google_uid = models.CharField(max_length=128, blank=True, db_index=True)
    avatar_url = models.URLField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email"], name="user_email_idx"),
            models.Index(fields=["google_uid"], name="user_google_uid_idx"),
        ]

    def __str__(self):
        return self.email

    @property
    def display_name(self):
        return self.name or self.email.split("@")[0]


# ──────────────────────────────────────────────────────────────────────────────
# Vehicle Image
# ──────────────────────────────────────────────────────────────────────────────

def vehicle_image_upload_path(instance, filename):
    """Store objects under vehicle-images/<user_id>/<uuid>.<ext>"""
    ext = filename.rsplit(".", 1)[-1].lower()
    new_name = f"{uuid.uuid4()}.{ext}"
    return f"vehicle-images/{instance.user_id}/{new_name}"


class VehicleImage(models.Model):
    """Stores metadata for a vehicle image uploaded to S3."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ANALYZING = "analyzing", "Analyzing"
        ANALYZED = "analyzed", "Analyzed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="vehicle_images",
    )
    # The image field — stored in S3 when AWS credentials are configured,
    # or local media/ folder in development.
    image = models.ImageField(upload_to=vehicle_image_upload_path)
    # Convenience field: the final S3 URL (or local path) after upload.
    image_url = models.URLField(max_length=1000, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    class Meta:
        verbose_name = "Vehicle Image"
        verbose_name_plural = "Vehicle Images"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["user", "uploaded_at"], name="vi_user_uploaded_idx"),
            models.Index(fields=["status"], name="vi_status_idx"),
        ]

    def __str__(self):
        return f"VehicleImage #{self.pk} — {self.user.email}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Populate image_url from the storage backend after save.
        if self.image and not self.image_url:
            try:
                self.image_url = self.image.url
                VehicleImage.objects.filter(pk=self.pk).update(image_url=self.image_url)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# Damage Insight (Gemini analysis result)
# ──────────────────────────────────────────────────────────────────────────────

class DamageInsight(models.Model):
    """
    Stores the structured Gemini response for a single VehicleImage.

    A VehicleImage may have multiple DamageInsight rows (one per detected part),
    but usually just one primary insight is created per analysis.
    """

    class Severity(models.TextChoices):
        MINOR = "minor", "Minor"
        MODERATE = "moderate", "Moderate"
        MAJOR = "major", "Major"
        UNKNOWN = "unknown", "Unknown"

    vehicle_image = models.ForeignKey(
        VehicleImage,
        on_delete=models.CASCADE,
        related_name="damage_insights",
    )
    detected_part = models.CharField(
        max_length=100,
        blank=True,
        help_text="E.g. bumper, door, headlight, windshield, fender …",
    )
    damage_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="E.g. scratch, dent, crack, shatter …",
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.UNKNOWN,
    )
    confidence = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
    # Full raw JSON blob from Gemini
    raw_gemini_response = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Damage Insight"
        verbose_name_plural = "Damage Insights"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["vehicle_image"], name="di_vehicle_image_idx"),
            models.Index(fields=["severity"], name="di_severity_idx"),
        ]

    def __str__(self):
        return f"DamageInsight #{self.pk} — {self.detected_part} ({self.severity})"


# ──────────────────────────────────────────────────────────────────────────────
# Claim Estimate
# ──────────────────────────────────────────────────────────────────────────────

class ClaimEstimate(models.Model):
    """Insurance cost estimate derived from a DamageInsight."""

    damage_insight = models.ForeignKey(
        DamageInsight,
        on_delete=models.CASCADE,
        related_name="claim_estimates",
    )
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="INR")
    calculation_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Claim Estimate"
        verbose_name_plural = "Claim Estimates"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["damage_insight"], name="ce_insight_idx"),
        ]

    def __str__(self):
        return f"ClaimEstimate #{self.pk} — {self.currency} {self.estimated_cost}"


# ──────────────────────────────────────────────────────────────────────────────
# Chatbot Conversations & Messages
# ──────────────────────────────────────────────────────────────────────────────

class ChatConversation(models.Model):
    """A multi-turn chat session with the AI Assistant."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_conversations",
    )
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Chat Conversation"
        verbose_name_plural = "Chat Conversations"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="chat_conv_user_idx"),
        ]

    def __str__(self):
        return f"ChatConversation #{self.pk} — {self.user.email} ({self.title})"


class ChatMessage(models.Model):
    """An individual message in a ChatConversation."""

    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
    ]

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="chat_msg_conv_idx"),
        ]

    def __str__(self):
        return f"ChatMessage #{self.pk} [{self.role}]: {self.content[:40]}"

