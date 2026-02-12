"""OpenAI GPT-4o-mini relevance checker (paid)."""

from __future__ import annotations

import httpx

from src.relevance._base import RelevanceChecker

_API_URL = "https://api.openai.com/v1/chat/completions"


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

    async def close(self) -> None:
        await self._client.aclose()
