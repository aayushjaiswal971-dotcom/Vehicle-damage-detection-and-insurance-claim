"""
core/views.py

All views for the Vehicle Damage & Insurance Claim Django app.

Protected views (dashboard, upload, history, result) require login.
Google OAuth is handled entirely by django-allauth at /accounts/google/login/.
"""

import base64
import io
import logging

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .forms import VehicleImageUploadForm
from .models import ClaimEstimate, DamageInsight, VehicleImage

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Landing / Login
# ──────────────────────────────────────────────────────────────────────────────

def landing(request):
    """Root URL: redirect authenticated users to dashboard, others to login."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "login.html")


def login_view(request):
    """Render the login page and handle credentials login or Google OAuth redirect."""
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            return redirect("core:dashboard")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "login.html")


def logout_view(request):
    """Log out and redirect to login page."""
    auth_logout(request)
    return redirect("core:login")


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@login_required(login_url="core:login")
def dashboard(request):
    """Main dashboard: shows upload form + the user's assessment history."""
    recent_images = (
        VehicleImage.objects.filter(user=request.user)
        .prefetch_related("damage_insights__claim_estimates")
        .order_by("-uploaded_at")[:20]
    )

    history = []
    for vi in recent_images:
        insight = vi.damage_insights.first()
        estimate = None
        if insight:
            estimate = insight.claim_estimates.first()
        history.append({
            "vehicle_image": vi,
            "insight": insight,
            "estimate": estimate,
        })

    form = VehicleImageUploadForm()
    return render(request, "dashboard.html", {
        "history": history,
        "form": form,
        "username": request.user.display_name,
        "avatar_url": request.user.avatar_url,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Upload (AJAX endpoint)
# ──────────────────────────────────────────────────────────────────────────────

@login_required(login_url="core:login")
@require_POST
def upload_image(request):
    """
    Accepts a multipart file upload OR a base64-encoded image blob.
    Saves the image to S3 (or local media/ in dev).
    The post_save signal automatically triggers Gemini analysis.

    Returns JSON:
        { success: true, vehicle_image_id: <id> }
        { success: false, message: "..." }
    """
    form = VehicleImageUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = "; ".join(
            f"{f}: {', '.join(errs)}" for f, errs in form.errors.items()
        )
        return JsonResponse({"success": False, "message": errors}, status=400)

    image_file = form.cleaned_data.get("image")
    image_data_b64 = form.cleaned_data.get("image_data", "").strip()

    try:
        if image_file:
            # ── Standard file upload ────────────────────────────────────────
            vehicle_image = VehicleImage(user=request.user)
            vehicle_image.image.save(image_file.name, image_file, save=True)
        else:
            # ── Camera / base64 blob ────────────────────────────────────────
            # Strip data-URI prefix if present: "data:image/jpeg;base64,..."
            if "," in image_data_b64:
                header, image_data_b64 = image_data_b64.split(",", 1)
                # Extract mime type from header
                mime_part = header.split(":")[1].split(";")[0] if ":" in header else "image/jpeg"
                ext = mime_part.split("/")[-1].replace("jpeg", "jpg")
            else:
                ext = "jpg"

            raw_bytes = base64.b64decode(image_data_b64)
            filename = f"camera_{request.user.pk}.{ext}"
            content = ContentFile(raw_bytes, name=filename)

            vehicle_image = VehicleImage(user=request.user)
            vehicle_image.image.save(filename, content, save=True)

    except Exception as exc:
        logger.error("Image upload failed for user %s: %s", request.user.email, exc, exc_info=True)
        return JsonResponse({"success": False, "message": f"Upload failed: {exc}"}, status=500)

    return JsonResponse({
        "success": True,
        "vehicle_image_id": vehicle_image.pk,
        "status": vehicle_image.status,
        "message": "Image uploaded. Analysis in progress…",
    })


# ──────────────────────────────────────────────────────────────────────────────
# Poll result (AJAX)
# ──────────────────────────────────────────────────────────────────────────────

@login_required(login_url="core:login")
@require_GET
def image_result(request, pk):
    """
    Return JSON with the analysis result for a given VehicleImage.

    Poll this endpoint after upload until status != 'analyzing'.
    """
    vi = get_object_or_404(VehicleImage, pk=pk, user=request.user)

    if vi.status == "pending" or vi.status == "analyzing":
        return JsonResponse({"success": True, "status": vi.status, "ready": False})

    if vi.status == "failed":
        return JsonResponse({
            "success": False,
            "status": "failed",
            "message": "Analysis failed. Please try again.",
        })

    insight = vi.damage_insights.first()
    if not insight:
        return JsonResponse({"success": False, "message": "No analysis results found."})

    estimate = insight.claim_estimates.first()

    return JsonResponse({
        "success": True,
        "ready": True,
        "status": "analyzed",
        "damaged_part": insight.detected_part,
        "damage_type": insight.damage_type,
        "severity": insight.severity,
        "confidence": insight.confidence,
        "notes": insight.notes,
        "estimated_cost": float(estimate.estimated_cost) if estimate else 0,
        "currency": estimate.currency if estimate else "INR",
        "image_url": vi.image_url or (vi.image.url if vi.image else ""),
    })


# ──────────────────────────────────────────────────────────────────────────────
# History (JSON API)
# ──────────────────────────────────────────────────────────────────────────────

@login_required(login_url="core:login")
@require_GET
def history(request):
    """Return the full assessment history for the logged-in user as JSON."""
    images = (
        VehicleImage.objects.filter(user=request.user)
        .prefetch_related("damage_insights__claim_estimates")
        .order_by("-uploaded_at")
    )
    records = []
    for vi in images:
        insight = vi.damage_insights.first()
        estimate = insight.claim_estimates.first() if insight else None
        records.append({
            "id": vi.pk,
            "uploaded_at": vi.uploaded_at.isoformat(),
            "status": vi.status,
            "image_url": vi.image_url,
            "damaged_part": insight.detected_part if insight else None,
            "damage_type": insight.damage_type if insight else None,
            "severity": insight.severity if insight else None,
            "confidence": insight.confidence if insight else None,
            "estimated_cost": float(estimate.estimated_cost) if estimate else None,
            "currency": estimate.currency if estimate else "INR",
        })
    return JsonResponse({"success": True, "history": records})


# ──────────────────────────────────────────────────────────────────────────────
# Claim Estimator (Adapted from 21st.dev UI Calculator Template)
# ──────────────────────────────────────────────────────────────────────────────

def claim_estimator(request):
    """
    Renders the Vehicle Damage & Insurance Claim ROI Benchmarking Tool.
    Supports pre-filling from an analyzed VehicleImage via `?image_id=<id>`
    or direct manual entry parameters.
    """
    from .services.gemini_service import estimate_claim_breakdown

    image_id = request.GET.get("image_id")
    vehicle_image = None
    insight = None
    estimate = None
    is_prefilled = False

    # Default parameters
    vehicle_type = request.GET.get("vehicle_type", "sedan").lower()
    damaged_part = request.GET.get("damaged_part", "bumper").lower()
    damage_type = request.GET.get("damage_type", "dent").lower()
    severity = request.GET.get("severity", "moderate").lower()
    part_source = request.GET.get("part_source", "oem").lower()
    region_tier = request.GET.get("region_tier", "tier1").lower()
    paint_scope = request.GET.get("paint_scope", "single_panel").lower()
    hourly_rate = float(request.GET.get("hourly_rate", 0)) if request.GET.get("hourly_rate") else None
    notes = request.GET.get("notes", "")
    repair_rec = request.GET.get("repair_rec", "")

    if image_id and request.user.is_authenticated:
        try:
            vehicle_image = VehicleImage.objects.filter(pk=image_id, user=request.user).first()
            if vehicle_image:
                insight = vehicle_image.damage_insights.first()
                if insight:
                    is_prefilled = True
                    damaged_part = insight.detected_part or damaged_part
                    damage_type = insight.damage_type or damage_type
                    severity = insight.severity or severity
                    notes = insight.notes or notes
                    if hasattr(insight, "raw_gemini_response") and isinstance(insight.raw_gemini_response, dict):
                        repair_rec = insight.raw_gemini_response.get("repair_recommendation", "")
                estimate = vehicle_image.damage_insights.first().claim_estimates.first() if insight else None
        except Exception as exc:
            logger.warning("Could not load vehicle image #%s for user %s: %s", image_id, request.user, exc)

    # Calculate initial estimation & benchmark breakdown
    breakdown = estimate_claim_breakdown(
        vehicle_type=vehicle_type,
        damaged_part=damaged_part,
        damage_type=damage_type,
        severity=severity,
        part_source=part_source,
        region_tier=region_tier,
        paint_scope=paint_scope,
        hourly_rate=hourly_rate,
    )

    context = {
        "is_prefilled": is_prefilled,
        "vehicle_image": vehicle_image,
        "insight": insight,
        "estimate": estimate,
        "vehicle_type": vehicle_type,
        "damaged_part": damaged_part,
        "damage_type": damage_type,
        "severity": severity,
        "part_source": part_source,
        "region_tier": region_tier,
        "paint_scope": paint_scope,
        "hourly_rate": hourly_rate or breakdown["hourly_rate"],
        "notes": notes,
        "repair_recommendation": repair_rec,
        "breakdown": breakdown,
    }

    return render(request, "claim_estimator.html", context)


def calculate_claim_api(request):
    """
    JSON API endpoint for real-time recalculation in the claim estimator frontend.
    Accepts GET or POST with form parameters and returns calculated JSON.
    """
    from .services.gemini_service import estimate_claim_breakdown

    params = request.POST if request.method == "POST" else request.GET

    vehicle_type = params.get("vehicle_type", "sedan")
    damaged_part = params.get("damaged_part", "bumper")
    damage_type = params.get("damage_type", "dent")
    severity = params.get("severity", "moderate")
    part_source = params.get("part_source", "oem")
    region_tier = params.get("region_tier", "tier1")
    paint_scope = params.get("paint_scope", "single_panel")
    try:
        hourly_rate = float(params.get("hourly_rate", 0)) if params.get("hourly_rate") else None
    except ValueError:
        hourly_rate = None

    breakdown = estimate_claim_breakdown(
        vehicle_type=vehicle_type,
        damaged_part=damaged_part,
        damage_type=damage_type,
        severity=severity,
        part_source=part_source,
        region_tier=region_tier,
        paint_scope=paint_scope,
        hourly_rate=hourly_rate,
    )

    return JsonResponse({
        "success": True,
        "breakdown": breakdown,
    })


# ──────────────────────────────────────────────────────────────────────────────
# Chatbot Endpoints (Multi-turn conversational assistant with Gemini failover)
# ──────────────────────────────────────────────────────────────────────────────

CHAT_SYSTEM_INSTRUCTION = """
You are the ClaimSense AI Assistant, an expert virtual consultant built into the ClaimSense AI Vehicle Damage & Insurance Claim Estimation platform.

Your primary responsibilities:
1. Platform Guidance: Help users understand how to use ClaimSense AI (registering/logging in with Google Auth, uploading photos or capturing live vehicle images via camera, reading Gemini AI damage insights, and tuning repair parameters in the Claim Estimator & ROI Benchmarking tool).
2. Damage & Repair Advisory: Answer questions about vehicle body parts, damage types (scratches, dents, cracks, glass shattering, frame deformation), repair techniques (Paintless Dent Repair / PDR, panel respraying, blending, structural pulling), and repair quality grades (OEM genuine vs. certified aftermarket vs. recycled parts).
3. Insurance Claim Clarifications: Explain how insurance claims operate (cashless network garages vs reimbursement, compulsory and voluntary deductibles, surveyor inspection process, total loss vs constructive loss, and how claiming affects No-Claim Bonus / NCB).
4. Disclaimer: Clearly state when quoting figures that all cost estimates and timelines are AI-assisted benchmarks, not guaranteed insurance settlement amounts or binding contractor quotes.
5. Scope: Be professional, polite, concise, and friendly. If a user asks about topics completely unrelated to vehicles, automobiles, vehicle damage, repairs, or insurance, politely decline and steer them back to ClaimSense AI capabilities.
""".strip()


@login_required(login_url="core:login")
@require_POST
def chat_api(request):
    """
    POST /api/chat/
    Accepts JSON: { "message": "...", "conversation_id": <int|null> }
    Returns JSON: { "success": true, "conversation_id": <id>, "reply": "...", "message_id": <id> }
    """
    import json
    import html
    from django.core.cache import cache
    from .models import ChatConversation, ChatMessage
    from .services.gemini_client import gemini_client, GeminiServiceUnavailableError, GeminiError

    # 1. Rate Limiting: max 20 messages per minute per user
    user_id = request.user.pk
    rate_key = f"chat_rate_limit_user_{user_id}"
    msg_count = cache.get(rate_key, 0)
    if msg_count >= 20:
        return JsonResponse({
            "success": False,
            "message": "You are sending messages too quickly. Please wait a moment before trying again."
        }, status=429)

    cache.set(rate_key, msg_count + 1, timeout=60)

    # 2. Parse and validate input
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = request.POST

    raw_message = str(data.get("message", "")).strip()
    if not raw_message:
        return JsonResponse({"success": False, "message": "Message cannot be empty."}, status=400)

    if len(raw_message) > 1000:
        return JsonResponse({
            "success": False,
            "message": "Message exceeds maximum allowed length of 1000 characters."
        }, status=400)

    # Sanitize message
    clean_message = html.escape(raw_message)
    conversation_id = data.get("conversation_id")

    # 3. Retrieve or create conversation
    conv = None
    if conversation_id:
        conv = ChatConversation.objects.filter(pk=conversation_id, user=request.user).first()

    if not conv:
        # Title from first 5-6 words
        title_words = clean_message.split()[:6]
        title = " ".join(title_words) if title_words else "New Conversation"
        if len(title) > 40:
            title = title[:40] + "..."
        conv = ChatConversation.objects.create(user=request.user, title=title)

    # 4. Save user message
    ChatMessage.objects.create(
        conversation=conv,
        role="user",
        content=clean_message,
    )

    # 5. Build dynamic system instruction with user's latest assessment context
    system_instruction = CHAT_SYSTEM_INSTRUCTION
    try:
        latest_image = (
            VehicleImage.objects.filter(user=request.user)
            .prefetch_related("damage_insights__claim_estimates")
            .order_by("-uploaded_at")
            .first()
        )
        if latest_image:
            insight = latest_image.damage_insights.first()
            if insight:
                estimate = insight.claim_estimates.first()
                cost_str = f"₹{estimate.estimated_cost:,.0f}" if estimate else "N/A"
                rec = insight.raw_gemini_response.get("repair_recommendation", "") if isinstance(insight.raw_gemini_response, dict) else ""
                user_context = (
                    f"\n\n[Active User Context]:\n"
                    f"- User Name: {request.user.display_name}\n"
                    f"- Most Recent Assessment (Image #{latest_image.pk}):\n"
                    f"  * Detected Part: {insight.detected_part}\n"
                    f"  * Damage Type: {insight.damage_type}\n"
                    f"  * Severity: {insight.severity}\n"
                    f"  * AI Confidence: {insight.confidence * 100:.0f}%\n"
                    f"  * Estimated Cost: {cost_str}\n"
                    f"  * Damage Notes: {insight.notes}\n"
                    f"  * Repair Recommendation: {rec}\n"
                    f"Refer to this context naturally when the user asks questions about their vehicle, damages, or costs."
                )
                system_instruction += user_context
    except Exception as exc:
        logger.debug("Could not attach user assessment context to chat: %s", exc)

    # 6. Gather last 10 messages for conversation context
    recent_msgs = conv.messages.order_by("-created_at")[:10]
    messages_payload = []
    for m in reversed(recent_msgs):
        messages_payload.append({
            "role": m.role,
            "content": m.content,
        })

    # 7. Call Gemini via multi-key failover manager
    try:
        reply_text = gemini_client.chat(
            messages=messages_payload,
            system_instruction=system_instruction,
            temperature=0.7,
            max_output_tokens=1024,
        )

        # Save assistant message
        assistant_msg = ChatMessage.objects.create(
            conversation=conv,
            role="assistant",
            content=reply_text,
        )
        conv.save(update_fields=["updated_at"])

        return JsonResponse({
            "success": True,
            "conversation_id": conv.pk,
            "reply": reply_text,
            "message_id": assistant_msg.pk,
        })

    except GeminiServiceUnavailableError as exc:
        logger.warning("All Gemini keys unavailable for chat: %s", exc)
        return JsonResponse({
            "success": False,
            "message": "The AI assistant is temporarily busy or rate-limited. Please try again in a moment."
        }, status=503)
    except Exception as exc:
        logger.error("Error generating chat response: %s", exc, exc_info=True)
        return JsonResponse({
            "success": False,
            "message": "Sorry, an unexpected error occurred while processing your request."
        }, status=500)


@login_required(login_url="core:login")
@require_GET
def chat_history_api(request):
    """
    GET /api/chat/history/?conversation_id=<id>
    Loads message history for an existing conversation or the user's latest conversation.
    """
    from .models import ChatConversation

    conv_id = request.GET.get("conversation_id")
    conv = None
    if conv_id:
        conv = ChatConversation.objects.filter(pk=conv_id, user=request.user).first()
    else:
        conv = ChatConversation.objects.filter(user=request.user).order_by("-updated_at").first()

    if not conv:
        return JsonResponse({"success": True, "conversation_id": None, "messages": []})

    messages_data = [
        {
            "id": m.pk,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.strftime("%H:%M"),
        }
        for m in conv.messages.order_by("created_at")
    ]

    return JsonResponse({
        "success": True,
        "conversation_id": conv.pk,
        "title": conv.title,
        "messages": messages_data,
    })


@login_required(login_url="core:login")
@require_POST
def clear_chat_api(request):
    """
    POST /api/chat/clear/
    Clears all messages or deletes a specified conversation.
    """
    import json
    from .models import ChatConversation

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = request.POST

    conv_id = data.get("conversation_id")
    if conv_id:
        ChatConversation.objects.filter(pk=conv_id, user=request.user).delete()
    else:
        ChatConversation.objects.filter(user=request.user).delete()

    return JsonResponse({"success": True, "message": "Conversation history cleared."})


