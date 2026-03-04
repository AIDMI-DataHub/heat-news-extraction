"""Gemini Flash relevance checker (free tier)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.relevance._base import RelevanceChecker

logger = logging.getLogger(__name__)

# Gemini free tier: 15 RPM for Flash.
# max_concurrent=1, min_interval=4.0 stays within limits.
_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 2.0  # seconds (longer for free tier)


class GeminiChecker(RelevanceChecker):
    """Relevance checker using Google Gemini Flash (free tier friendly).

    Parameters
    ----------
    api_key:
        Google AI API key.
    """

    def __init__(self, api_key: str) -> None:
        # Conservative rate limits for free tier
        super().__init__(max_concurrent=1, min_interval=4.0)
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    async def _call_llm(self, system: str, user: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(
                    _API_URL,
                    params={"key": self._api_key},
                    json={
                        "system_instruction": {"parts": [{"text": system}]},
                        "contents": [{"parts": [{"text": user}]}],
                        "generationConfig": {
                            "maxOutputTokens": 5,
                            "temperature": 0.0,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status == 429 or status >= 500:
                    wait = _INITIAL_BACKOFF * (2 ** attempt)
                    if attempt < _MAX_RETRIES - 1:
                        logger.debug(
                            "Gemini %d, retrying in %.1fs (attempt %d/%d)",
                            status, wait, attempt + 1, _MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue
                raise

        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        await self._client.aclose()
