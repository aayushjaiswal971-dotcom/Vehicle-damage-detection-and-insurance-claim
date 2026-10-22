"""
core/signals.py

Two signal handlers:
1. allauth social_account_updated / social_account_added
   → Populate User.google_uid, User.name, User.avatar_url from the Google profile.

2. post_save on VehicleImage (status=PENDING)
   → Trigger Gemini analysis synchronously, create DamageInsight + ClaimEstimate.
"""

import logging
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Google OAuth profile sync
# ──────────────────────────────────────────────────────────────────────────────

def _populate_user_from_google(sociallogin, **kwargs):
    """
    Called after allauth creates or updates a social account.
    Copies name, avatar_url, google_uid from the Google profile to User.
    """
    user = sociallogin.user
    account = sociallogin.account  # SocialAccount instance

    extra = account.extra_data or {}
    changed = False

    if not user.google_uid and account.uid:
        user.google_uid = account.uid
        changed = True

    google_name = extra.get("name") or extra.get("given_name", "")
    if google_name and not user.name:
        user.name = google_name
        changed = True

    picture = extra.get("picture", "")
    if picture and not user.avatar_url:
        user.avatar_url = picture
        changed = True

    if changed:
        user.save(update_fields=["google_uid", "name", "avatar_url"])
        logger.info("Updated Google profile fields for user %s", user.email)


def connect_allauth_signals():
    """
    Connect to allauth signals.  Called from AppConfig.ready() so that allauth
    has already registered its own signals by the time we hook in.
    """
    try:
        from allauth.socialaccount.signals import (
            social_account_added,
            social_account_updated,
        )

        social_account_added.connect(_populate_user_from_google)
        social_account_updated.connect(_populate_user_from_google)
        logger.debug("allauth Google profile signals connected.")
    except ImportError:
        logger.warning("allauth not installed — Google profile sync signal not connected.")


# ──────────────────────────────────────────────────────────────────────────────
# 2. Post-save → Gemini analysis
# ──────────────────────────────────────────────────────────────────────────────

@receiver(post_save, sender="core.VehicleImage")
def trigger_gemini_analysis(sender, instance, created, **kwargs):
    """
    After a new VehicleImage is saved with status=PENDING, kick off Gemini
    analysis synchronously.

    If you later add Celery/RQ, replace the body of this handler with:
        analyse_image_task.delay(instance.pk)
    """
    if not created:
        return
    if instance.status != "pending":
        return

    # Import here to avoid circular imports
    from core.models import ClaimEstimate, DamageInsight, VehicleImage
    from core.services.gemini_service import analyze_vehicle_image

    logger.info("Starting Gemini analysis for VehicleImage #%s", instance.pk)

    # Mark as analyzing
    VehicleImage.objects.filter(pk=instance.pk).update(status="analyzing")

    try:
        # Read image bytes from the storage backend
        image_file = instance.image
        image_file.open("rb")
        image_bytes = image_file.read()
        image_file.close()

        # Determine MIME type from extension
        name = instance.image.name.lower()
        if name.endswith(".png"):
            mime = "image/png"
        elif name.endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"

        result = analyze_vehicle_image(image_bytes=image_bytes, mime_type=mime)

    except Exception as exc:
        logger.error("Could not read image bytes for VehicleImage #%s: %s", instance.pk, exc)
        VehicleImage.objects.filter(pk=instance.pk).update(status="failed")
        return

    if not result["success"]:
        logger.error(
            "Gemini analysis failed for VehicleImage #%s: %s",
            instance.pk,
            result.get("error"),
        )
        VehicleImage.objects.filter(pk=instance.pk).update(status="failed")
        return

    # Save DamageInsight
    insight = DamageInsight.objects.create(
        vehicle_image=instance,
        detected_part=result["part"],
        damage_type=result["damage_type"],
        severity=result["severity"],
        confidence=result["confidence"],
        notes=result["notes"],
        raw_gemini_response=result["raw_response"],
    )

    # Save ClaimEstimate (midpoint of the range)
    low = result["estimated_cost_low"]
    high = result["estimated_cost_high"]
    midpoint = Decimal(str((low + high) // 2))
    ClaimEstimate.objects.create(
        damage_insight=insight,
        estimated_cost=midpoint,
        currency="INR",
        calculation_notes=(
            f"Estimated range: ₹{low:,} – ₹{high:,} "
            f"based on severity={result['severity']}, damage_type={result['damage_type']}."
        ),
    )

    VehicleImage.objects.filter(pk=instance.pk).update(status="analyzed")
    logger.info(
        "Gemini analysis complete for VehicleImage #%s: %s / %s / %s",
        instance.pk,
        result["part"],
        result["damage_type"],
        result["severity"],
    )
