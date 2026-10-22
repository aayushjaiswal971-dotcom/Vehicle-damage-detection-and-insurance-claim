"""
core/services/gemini_client.py

Centralized Gemini API Manager with multi-key automatic failover and cooldown rotation.

Features:
- Owns all Gemini API calls across the application.
- Loads up to 3 API keys in priority order (Index 1 -> Index 2 -> Index 3).
- Automatically retries the exact same request on key exhaustion (429, 401, 403, RESOURCE_EXHAUSTED).
- Applies thread-safe and Django-cache-backed cooldown periods (60s for rate limits, 3600s for invalid/exhausted keys).
- Preserves non-key errors (400, safety filters, malformed input) without failing over.
- Provides friendly user-facing messages when all keys are exhausted.
- NEVER logs or leaks API key secrets (only logs key index 1, 2, or 3).
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Error keywords that trigger key failover
FAILOVER_ERROR_KEYWORDS = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "rate_limit",
    "401",
    "403",
    "permission_denied",
    "api key not valid",
    "invalid api key",
    "apikey not valid",
    "unauthenticated",
    "billing",
)

# Cooldown durations (seconds)
COOLDOWN_RATE_LIMIT_SEC = 60
COOLDOWN_QUOTA_EXHAUSTED_SEC = 3600


class GeminiError(Exception):
    """Base exception for Gemini service errors."""
    pass


class GeminiServiceUnavailableError(GeminiError):
    """Raised when all configured Gemini API keys are exhausted or unavailable."""
    pass


class GeminiClientManager:
    """
    Thread-safe manager for multi-key Gemini API calls with automatic failover.
    """

    _lock = threading.Lock()
    _clients: Dict[int, Any] = {}
    _local_cooldowns: Dict[int, float] = {}

    def __init__(self):
        pass

    @property
    def configured_keys(self) -> List[Tuple[int, str]]:
        """
        Returns a list of (index_1_based, key_string) from Django settings.
        Never returns empty or whitespace-only keys.
        """
        keys = getattr(settings, "GEMINI_API_KEYS", [])
        if not keys:
            # Fallback to single key setting if available
            single = getattr(settings, "GEMINI_API_KEY", "")
            if single and single.strip():
                keys = [single.strip()]
        return [(idx + 1, k) for idx, k in enumerate(keys) if k and k.strip()]

    def _cache_key(self, index: int) -> str:
        return f"gemini_key_cooldown_idx_{index}"

    def is_key_available(self, index: int) -> bool:
        """
        Checks if a key index is currently active and not in cooldown.
        Checks both Django cache and local memory.
        """
        now = time.time()
        # 1. Check in-memory cooldown
        with self._lock:
            local_exp = self._local_cooldowns.get(index, 0)
            if local_exp > now:
                return False
            elif local_exp > 0:
                # Expired in memory
                del self._local_cooldowns[index]
                logger.info("Gemini Key #%d cooldown expired (local memory). Rejoining rotation.", index)

        # 2. Check Django cache
        try:
            cache_exp = cache.get(self._cache_key(index))
            if cache_exp and float(cache_exp) > now:
                return False
            elif cache_exp:
                cache.delete(self._cache_key(index))
                logger.info("Gemini Key #%d cooldown expired (cache). Rejoining rotation.", index)
        except Exception as exc:
            logger.debug("Cache check failed for key cooldown: %s", exc)

        return True

    def mark_key_cooldown(self, index: int, reason: str, duration_sec: int = COOLDOWN_RATE_LIMIT_SEC) -> None:
        """
        Places a key into cooldown across threads and cache.
        """
        expiry = time.time() + duration_sec
        with self._lock:
            self._local_cooldowns[index] = expiry

        try:
            cache.set(self._cache_key(index), expiry, timeout=duration_sec)
        except Exception as exc:
            logger.debug("Cache set failed for key cooldown: %s", exc)

        logger.warning(
            "Gemini Key #%d marked unavailable for %d seconds. Reason: %s",
            index, duration_sec, reason
        )

    def reset_cooldowns(self) -> None:
        """Resets all key cooldowns (useful for unit testing and manual resets)."""
        with self._lock:
            self._local_cooldowns.clear()
            self._clients.clear()
        for idx, _ in self.configured_keys:
            try:
                cache.delete(self._cache_key(idx))
            except Exception:
                pass
        logger.info("All Gemini key cooldowns have been reset.")

    def _get_sdk_client(self, index: int, api_key: str):
        """Initializes or retrieves cached google-genai client for a given key."""
        with self._lock:
            if index not in self._clients:
                try:
                    from google import genai
                    self._clients[index] = genai.Client(api_key=api_key)
                except ImportError as exc:
                    raise GeminiError("google-genai SDK is not installed. Run: pip install google-genai") from exc
            return self._clients[index]

    def _is_failover_error(self, exc: Exception) -> Tuple[bool, int]:
        """
        Determines whether an exception is a rate limit/quota/auth issue requiring failover.
        Returns (is_failover, cooldown_seconds).
        """
        err_msg = str(exc).lower()

        # Check status code if available on exception (e.g. google.genai.errors.APIError)
        status_code = getattr(exc, "code", getattr(exc, "status_code", None))
        if status_code in (429,):
            return True, COOLDOWN_RATE_LIMIT_SEC
        if status_code in (401, 403):
            return True, COOLDOWN_QUOTA_EXHAUSTED_SEC

        for kw in FAILOVER_ERROR_KEYWORDS:
            if kw in err_msg:
                if "429" in err_msg or "rate" in err_msg:
                    return True, COOLDOWN_RATE_LIMIT_SEC
                return True, COOLDOWN_QUOTA_EXHAUSTED_SEC

        return False, 0

    def execute_with_failover(self, call_fn) -> Any:
        """
        Executes a callable `call_fn(client, key_index)` with automatic multi-key failover.
        """
        keys = self.configured_keys
        if not keys:
            raise GeminiServiceUnavailableError(
                "No Gemini API keys are configured. Please set GEMINI_API_KEY_1 in your .env file."
            )

        attempted_indices = []

        for index, key_str in keys:
            if not self.is_key_available(index):
                logger.debug("Gemini Key #%d is in cooldown, skipping.", index)
                continue

            attempted_indices.append(index)
            logger.info("Executing Gemini API request using Key #%d...", index)

            try:
                client = self._get_sdk_client(index, key_str)
                result = call_fn(client, index)
                logger.debug("Gemini API call succeeded with Key #%d.", index)
                return result

            except Exception as exc:
                is_failover, cooldown_sec = self._is_failover_error(exc)
                if is_failover:
                    logger.warning(
                        "Gemini Key #%d failed with transient/quota error: %s. Initiating failover...",
                        index, exc
                    )
                    self.mark_key_cooldown(index, reason=str(exc), duration_sec=cooldown_sec)
                    # Loop continues to next key
                    continue
                else:
                    # Non-key error (e.g. bad request, safety block, invalid syntax) -> Do NOT fail over
                    logger.error("Gemini API call failed with non-key error (no failover): %s", exc)
                    raise

        # If all keys were tried or in cooldown
        logger.error(
            "All Gemini API keys are exhausted or in cooldown. Attempted indices: %s",
            attempted_indices
        )
        raise GeminiServiceUnavailableError(
            "The AI service is currently busy or rate-limited. Please try again in a few moments."
        )

    # ──────────────────────────────────────────────────────────────────────────
    # High-level API Methods
    # ──────────────────────────────────────────────────────────────────────────

    def generate_with_image(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        mime_type: str = "image/jpeg",
        image_url: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.1,
        max_output_tokens: int = 512,
        system_instruction: Optional[str] = None,
    ) -> str:
        """
        Sends an image + prompt to Gemini for multimodal damage analysis with automatic failover.
        Returns the raw text response from the model.
        """
        from google.genai import types

        def _call(client, key_idx):
            parts = []
            if image_bytes:
                parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))
            elif image_url:
                parts.append(types.Part.from_uri(file_uri=image_url, mime_type=mime_type))

            parts.append(types.Part.from_text(text=prompt))

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = client.models.generate_content(
                model=model,
                contents=[types.Content(parts=parts, role="user")],
                config=config,
            )
            return response.text

        return self.execute_with_failover(_call)

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        max_output_tokens: int = 1024,
    ) -> str:
        """
        Sends a multi-turn chat message history to Gemini with automatic failover.
        `messages` format: [{"role": "user"|"assistant"|"model", "content": "..."}, ...]
        """
        from google.genai import types

        def _call(client, key_idx):
            contents = []
            for msg in messages:
                raw_role = msg.get("role", "user").lower()
                role = "user" if raw_role in ("user", "human") else "model"
                text = msg.get("content", "").strip()
                if text:
                    contents.append(
                        types.Content(
                            parts=[types.Part.from_text(text=text)],
                            role=role,
                        )
                    )

            if not contents:
                raise GeminiError("No valid chat messages provided.")

            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            if system_instruction:
                config.system_instruction = system_instruction

            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
            return response.text

        return self.execute_with_failover(_call)


# Global singleton instance
gemini_client = GeminiClientManager()
