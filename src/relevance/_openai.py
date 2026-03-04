"""OpenAI GPT-4o-mini relevance checker (paid)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from src.relevance._base import RelevanceChecker

logger = logging.getLogger(__name__)

_API_URL = "https://api.openai.com/v1/chat/completions"

_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0  # seconds


class OpenAIChecker(RelevanceChecker):
    """Relevance checker using OpenAI GPT-4o-mini.

    Parameters
    ----------
    api_key:
        OpenAI API key.
    """

    def __init__(self, api_key: str) -> None:
        super().__init__(max_concurrent=5, min_interval=0.1)
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def _call_llm(self, system: str, user: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post(
                    _API_URL,
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        "max_tokens": 5,
                        "temperature": 0.0,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                if status == 429 or status >= 500:
                    # Use Retry-After header if provided, else exponential backoff
                    retry_after = exc.response.headers.get("retry-after")
                    if retry_after:
                        try:
                            wait = float(retry_after)
                        except ValueError:
                            wait = _INITIAL_BACKOFF * (2 ** attempt)
                    else:
                        wait = _INITIAL_BACKOFF * (2 ** attempt)
                    if attempt < _MAX_RETRIES - 1:
                        logger.debug(
                            "OpenAI %d, retrying in %.1fs (attempt %d/%d)",
                            status, wait, attempt + 1, _MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue
                # Non-retryable status or last attempt -- re-raise
                raise

        # Should not reach here, but just in case
        raise last_exc  # type: ignore[misc]

    async def close(self) -> None:
        await self._client.aclose()
