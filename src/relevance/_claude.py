"""Claude Haiku relevance checker (paid)."""

from __future__ import annotations

import httpx

from src.relevance._base import RelevanceChecker

_API_URL = "https://api.anthropic.com/v1/messages"


class ClaudeChecker(RelevanceChecker):
    """Relevance checker using Claude Haiku.

    Parameters
    ----------
    api_key:
        Anthropic API key.
    """

    def __init__(self, api_key: str) -> None:
        super().__init__(max_concurrent=5, min_interval=0.1)
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

    async def _call_llm(self, system: str, user: str) -> str:
        response = await self._client.post(
            _API_URL,
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 5,
                "temperature": 0.0,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]

    async def close(self) -> None:
        await self._client.aclose()
