"""LLM-based article relevance checking.

Provides a factory function to create the appropriate relevance checker
based on user configuration (environment variables).

Configuration
-------------
LLM_PROVIDER : str
    Which LLM to use for relevance checking. Supports single or combined:
    - ``gemini`` -- Google Gemini Flash (free tier)
    - ``openai`` (default) -- OpenAI GPT-4o-mini (paid)
    - ``claude`` -- Claude Haiku (paid)
    - ``none`` -- Skip LLM relevance check entirely
    Use ``+`` for multi-LLM consensus: ``openai+gemini``, ``openai+gemini+claude``

API keys (set the one matching your provider):
    GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
"""

from __future__ import annotations

import logging
import os

from src.relevance._base import RelevanceChecker

logger = logging.getLogger(__name__)

__all__ = ["create_relevance_checker", "RelevanceChecker"]


def _create_single_checker(provider: str) -> RelevanceChecker | None:
    """Create a single relevance checker for the given provider name.

    Returns None if the required API key is missing.
    """
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            logger.warning("GEMINI_API_KEY not set -- skipping Gemini checker")
            return None
        from src.relevance._gemini import GeminiChecker

        return GeminiChecker(api_key)

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            logger.warning("OPENAI_API_KEY not set -- skipping OpenAI checker")
            return None
        from src.relevance._openai import OpenAIChecker

        return OpenAIChecker(api_key)

    if provider == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set -- skipping Claude checker")
            return None
        from src.relevance._claude import ClaudeChecker

        return ClaudeChecker(api_key)

    logger.warning("Unknown provider %r -- skipped", provider)
    return None


def create_relevance_checker() -> RelevanceChecker | None:
    """Create a relevance checker based on environment configuration.

    Returns None if LLM_PROVIDER is "none" or if the required API key
    is missing (with a warning).

    Supports multi-LLM consensus via ``+`` separator:
        LLM_PROVIDER=openai+gemini  -> majority vote from both
    """
    provider = os.environ.get("LLM_PROVIDER", "openai").lower().strip()

    if provider == "none":
        logger.info("LLM relevance check disabled (LLM_PROVIDER=none)")
        return None

    # Multi-LLM consensus mode
    if "+" in provider:
        names = [p.strip() for p in provider.split("+") if p.strip()]
        checkers = [_create_single_checker(p) for p in names]
        checkers = [c for c in checkers if c is not None]

        if len(checkers) < 2:
            logger.warning(
                "Multi-LLM consensus needs 2+ checkers but only %d available "
                "(missing API keys?). Falling back to single checker.",
                len(checkers),
            )
            if checkers:
                logger.info("Using single checker: %s", names[0])
                return checkers[0]
            return None

        from src.relevance._consensus import ConsensusChecker

        logger.info(
            "Using multi-LLM consensus: %s (%d checkers, majority vote)",
            "+".join(names),
            len(checkers),
        )
        return ConsensusChecker(checkers)

    # Single provider mode
    checker = _create_single_checker(provider)
    if checker is not None:
        logger.info("Using %s for relevance checking", provider)
    else:
        logger.warning(
            "Could not create %s checker -- skipping LLM relevance check. "
            "Set LLM_PROVIDER=none to suppress this warning.",
            provider,
        )
    return checker
