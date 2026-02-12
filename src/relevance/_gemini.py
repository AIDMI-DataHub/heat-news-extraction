"""Gemini Flash relevance checker (free tier)."""

from __future__ import annotations

import httpx

from src.relevance._base import RelevanceChecker

# Gemini free tier: 15 RPM for Flash.
# max_concurrent=1, min_interval=4.0 stays within limits.
_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


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

    async def close(self) -> None:
        await self._client.aclose()
