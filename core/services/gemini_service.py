"""
core/services/gemini_service.py

Service layer for analysing vehicle images with the Google Gemini API.

Usage:
    from core.services.gemini_service import analyze_vehicle_image

    result = analyze_vehicle_image(image_bytes=raw_bytes, mime_type="image/jpeg")
    # or
    result = analyze_vehicle_image(image_url="https://…")

Returns a dict with keys:
    success       bool
    part          str   — e.g. "bumper", "door"
    damage_type   str   — e.g. "dent", "scratch"
    severity      str   — "minor" | "moderate" | "major"
    confidence    float — 0.0–1.0
    notes         str   — free-text notes from the model
    raw_response  dict  — full parsed JSON blob for DamageInsight.raw_gemini_response
    error         str   — only present when success=False
"""

import json
import logging
import re
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# ── Prompt ────────────────────────────────────────────────────────────────────
_ANALYSIS_PROMPT = """
You are an expert vehicle damage assessment AI.

Analyse the provided image of a vehicle and return ONLY a valid JSON object — no markdown, no explanation, no extra text.

The JSON must strictly follow this schema:
{
  "part": "<string — the primary damaged vehicle part: bumper | door | hood | headlight | windshield | fender | trunk | roof | mirror | wheel | unknown>",
  "damage_type": "<string — type of damage: scratch | dent | crack | shatter | deformation | paint_damage | missing_part | unknown>",
  "severity": "<string — exactly one of: minor | moderate | major>",
  "confidence": <float between 0.0 and 1.0>,
  "notes": "<string — one sentence describing the damage>",
  "repair_recommendation": "<string — concise repair recommendation, e.g., 'Paintless Dent Repair (PDR) with spot clear coat; no structural replacement needed.'>"
}

Rules:
- If no vehicle or damage is visible, set part="unknown", damage_type="unknown", severity="minor", confidence=0.0, notes="No vehicle damage detected.", repair_recommendation="No repairs required."
- Do NOT include any text outside the JSON object.
- severity definitions: minor = cosmetic only (small scratch/chip); moderate = structural but repairable; major = severe structural damage or safety risk.
""".strip()

# ── Cost Ranges (INR) used by claim estimation ────────────────────────────────
COST_RANGES = {
    ("minor",    "scratch"):         (3_000,   8_000),
    ("minor",    "dent"):            (5_000,  12_000),
    ("minor",    "paint_damage"):    (4_000,  10_000),
    ("moderate", "dent"):           (15_000,  40_000),
    ("moderate", "crack"):          (20_000,  50_000),
    ("moderate", "deformation"):    (25_000,  60_000),
    ("major",    "shatter"):        (50_000, 120_000),
    ("major",    "deformation"):    (60_000, 150_000),
    ("major",    "missing_part"):   (40_000, 100_000),
}
DEFAULT_COST_RANGES = {
    "minor":    (5_000,  15_000),
    "moderate": (15_000, 50_000),
    "major":    (50_000, 150_000),
}

# ── Benchmark Industry Lookup (Placeholder market averages) ──────────────────
# Structured reference costs by vehicle category and damage type
BENCHMARK_PRICING = {
    "hatchback": {"minor": 6_500, "moderate": 22_000, "major": 65_000, "mult": 0.85},
    "sedan":     {"minor": 8_500, "moderate": 28_000, "major": 85_000, "mult": 1.00},
    "suv":       {"minor": 11_000, "moderate": 38_000, "major": 110_000, "mult": 1.25},
    "luxury":    {"minor": 22_000, "moderate": 75_000, "major": 220_000, "mult": 2.20},
    "commercial":{"minor": 7_500, "moderate": 26_000, "major": 70_000, "mult": 0.90},
}


def estimate_claim_breakdown(
    vehicle_type: str = "sedan",
    damaged_part: str = "bumper",
    damage_type: str = "dent",
    severity: str = "moderate",
    part_source: str = "oem",
    region_tier: str = "tier1",
    paint_scope: str = "single_panel",
    hourly_rate: Optional[float] = None,
) -> dict:
    """
    Calculate an itemized repair cost breakdown, estimate range, and industry benchmark comparison.
    """
    vehicle_type = vehicle_type.lower() if vehicle_type in BENCHMARK_PRICING else "sedan"
    v_data = BENCHMARK_PRICING[vehicle_type]
    v_mult = v_data["mult"]

    # Base low & high
    base_low, base_high = _estimate_cost(severity, damage_type)

    # Multipliers
    part_mults = {"oem": 1.25, "aftermarket": 1.0, "recycled": 0.75}
    p_mult = part_mults.get(part_source.lower(), 1.0)

    region_rates = {"tier1": 850.0, "tier2": 600.0, "tier3": 450.0}
    applied_rate = hourly_rate if hourly_rate and hourly_rate > 0 else region_rates.get(region_tier.lower(), 700.0)

    paint_costs = {"spot": 2500, "single_panel": 6000, "multi_panel": 14000, "none": 0}
    paint_base = paint_costs.get(paint_scope.lower(), 5000) * v_mult

    # Estimate labor hours based on severity and damage
    labor_hours_map = {
        "minor": 3.5,
        "moderate": 8.0,
        "major": 22.0,
    }
    labor_hours = labor_hours_map.get(severity.lower(), 6.0)
    labor_cost = round(labor_hours * applied_rate)

    # Parts cost base
    parts_cost = round((base_low * 0.45 * v_mult * p_mult))

    # Paint cost
    paint_cost = round(paint_base)

    # Consumables & Workshop admin fee
    consumables = round((parts_cost + labor_cost + paint_cost) * 0.06)

    subtotal = parts_cost + labor_cost + paint_cost + consumables
    taxes = round(subtotal * 0.18)  # 18% GST
    total_estimated = subtotal + taxes

    min_est = round(total_estimated * 0.88)
    max_est = round(total_estimated * 1.15)

    # Industry benchmarks for this category & severity
    market_avg = round(v_data.get(severity.lower(), 30_000) * (1.0 if part_source == "aftermarket" else 1.15))
    dealer_avg = round(market_avg * 1.35)
    independent_avg = round(market_avg * 0.82)

    # Delta vs market average
    diff_pct = round(((total_estimated - market_avg) / market_avg) * 100, 1)

    return {
        "total_estimated": total_estimated,
        "min_estimated": min_est,
        "max_estimated": max_est,
        "parts_cost": parts_cost,
        "labor_cost": labor_cost,
        "labor_hours": labor_hours,
        "hourly_rate": applied_rate,
        "paint_cost": paint_cost,
        "consumables": consumables,
        "taxes": taxes,
        "market_avg": market_avg,
        "dealer_avg": dealer_avg,
        "independent_avg": independent_avg,
        "diff_pct": diff_pct,
        "is_within_benchmark": abs(diff_pct) <= 20,
    }


from .gemini_client import gemini_client, GeminiError, GeminiServiceUnavailableError


def _parse_gemini_json(text: str) -> dict:
    """
    Extract a JSON object from the model's text response.

    The model is instructed to return only JSON, but we defensively strip
    any surrounding markdown code fences if present.
    """
    # Strip markdown fences
    text = re.sub(r"```(?:json)?", "", text).strip()
    # Find the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in Gemini response: {text!r}")
    return json.loads(match.group())


def _estimate_cost(severity: str, damage_type: str) -> tuple[int, int]:
    """Return (low, high) INR cost range for a severity + damage_type pair."""
    key = (severity.lower(), damage_type.lower())
    if key in COST_RANGES:
        return COST_RANGES[key]
    return DEFAULT_COST_RANGES.get(severity.lower(), (5_000, 50_000))


def analyze_vehicle_image(
    image_bytes: Optional[bytes] = None,
    mime_type: str = "image/jpeg",
    image_url: Optional[str] = None,
) -> dict:
    """
    Send a vehicle image to Gemini for damage analysis with automatic multi-key failover.

    Parameters
    ----------
    image_bytes : bytes, optional
        Raw image data. Provide either this or `image_url`.
    mime_type : str
        MIME type of the image bytes (e.g. "image/jpeg", "image/png").
    image_url : str, optional
        Publicly accessible URL of the image. Used only when image_bytes is None.

    Returns
    -------
    dict with keys: success, part, damage_type, severity, confidence, notes,
                    repair_recommendation, raw_response, estimated_cost_low,
                    estimated_cost_high, error (on failure)
    """
    if not image_bytes and not image_url:
        return _error_result("No image data provided — supply image_bytes or image_url.")

    try:
        raw_text = gemini_client.generate_with_image(
            prompt=_ANALYSIS_PROMPT,
            image_bytes=image_bytes,
            mime_type=mime_type,
            image_url=image_url,
            temperature=0.1,
            max_output_tokens=512,
        )
        logger.debug("Gemini raw response: %s", raw_text)

        parsed = _parse_gemini_json(raw_text)

        # Normalise / validate fields
        part = str(parsed.get("part", "unknown")).lower().strip()
        damage_type = str(parsed.get("damage_type", "unknown")).lower().strip()
        severity = str(parsed.get("severity", "minor")).lower().strip()
        if severity not in ("minor", "moderate", "major"):
            severity = "minor"
        confidence = float(parsed.get("confidence", 0.0))
        notes = str(parsed.get("notes", ""))
        repair_recommendation = str(parsed.get("repair_recommendation", ""))

        cost_low, cost_high = _estimate_cost(severity, damage_type)

        return {
            "success": True,
            "part": part,
            "damage_type": damage_type,
            "severity": severity,
            "confidence": confidence,
            "notes": notes,
            "repair_recommendation": repair_recommendation,
            "raw_response": parsed,
            "estimated_cost_low": cost_low,
            "estimated_cost_high": cost_high,
        }

    except GeminiServiceUnavailableError as exc:
        logger.warning("All Gemini keys unavailable for damage analysis: %s", exc)
        return _error_result("The AI analysis service is temporarily busy. Please retry in a few moments.")
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse Gemini JSON response: %s", exc)
        return _error_result(f"Gemini returned invalid response structure: {exc}")
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini API error during image analysis: %s", exc, exc_info=True)
        return _error_result(f"AI Analysis error: {exc}")


def _error_result(message: str) -> dict:
    return {
        "success": False,
        "part": "unknown",
        "damage_type": "unknown",
        "severity": "minor",
        "confidence": 0.0,
        "notes": "",
        "repair_recommendation": "",
        "raw_response": {},
        "estimated_cost_low": 0,
        "estimated_cost_high": 0,
        "error": message,
    }

