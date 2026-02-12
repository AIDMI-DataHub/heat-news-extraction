"""Pre-extraction title relevance filter.

Checks article titles for heat-signal words before spending resources on
full-text extraction.  An article must contain at least one heat-signal
word in its title to be considered worth extracting.

This is intentionally a FAST, keyword-based check (no LLM, no API calls).
It runs on thousands of titles in milliseconds.
"""

from __future__ import annotations

import logging
import re

from src.models.article import ArticleRef

logger = logging.getLogger(__name__)

# Heat-signal words across languages.  If a title contains at least one
# of these (case-insensitive), the article is considered potentially
# heat-related and worth extracting.
#
# These are words that are UNAMBIGUOUSLY about heat/temperature.
# Generic words like "alert", "school closed", "power cut" are
# deliberately excluded because they match non-heat content.
_HEAT_SIGNALS: list[str] = [
    # English
    "heat", "heatwave", "heat wave", "hot", "scorching", "sweltering",
    "sunstroke", "sun stroke", "heatstroke", "heat stroke",
    "temperature", "mercury", "celsius", "loo ",  # trailing space to avoid matching "look", "loop"
    "drought", "water crisis", "water shortage",

    # Hindi
    "गर्मी", "लू", "तापमान", "पारा", "सूर्याघात", "तापाघात",
    "हीट", "धूप", "उष्ण", "ग्रीष्म",

    # Tamil
    "வெப்பம்", "வெப்ப அலை", "கோடை", "வெயில்",

    # Telugu
    "వేడి", "ఉష్ణ", "ఎండ", "సూర్యాఘాతం",

    # Bengali
    "গরম", "তাপ", "তাপমাত্রা", "দাবদাহ", "লু",

    # Marathi
    "उष्णता", "उन्हाळा", "तापमान", "ऊन",

    # Gujarati
    "ગરમી", "તાપમાન", "લૂ", "ઉષ્ણ",

    # Kannada
    "ಬಿಸಿ", "ಉಷ್ಣ", "ತಾಪಮಾನ", "ಬಿಸಿಗಾಳಿ",

    # Malayalam
    "ചൂട്", "ഉഷ്ണ", "താപനില", "വെയിൽ",

    # Odia
    "ଗରମ", "ତାପମାତ୍ରା", "ଉଷ୍ଣ",

    # Punjabi
    "ਗਰਮੀ", "ਤਾਪਮਾਨ", "ਲੂ",

    # Assamese
    "গৰম", "তাপমাত্ৰা",

    # Urdu
    "گرمی", "لو", "ہیٹ", "شدید گرمی",

    # Nepali
    "गर्मी", "तापक्रम", "लू",
]

# Compile into a single regex for fast matching.
# re.escape each term, join with |, compile case-insensitive.
_HEAT_PATTERN = re.compile(
    "|".join(re.escape(term) for term in _HEAT_SIGNALS),
    re.IGNORECASE,
)


def title_has_heat_signal(title: str) -> bool:
    """Return True if the title contains at least one heat-signal word."""
    return bool(_HEAT_PATTERN.search(title))


def filter_by_title_relevance(refs: list[ArticleRef]) -> list[ArticleRef]:
    """Filter article refs to only those with heat-relevant titles.

    This is a PRE-EXTRACTION filter -- it runs on titles only (no
    network calls) and discards articles that are clearly not about heat.

    Args:
        refs: Article references from collection.

    Returns:
        Subset of refs whose titles contain a heat-signal word.
    """
    relevant = [r for r in refs if title_has_heat_signal(r.title)]
    dropped = len(refs) - len(relevant)
    logger.info(
        "Title relevance filter: %d -> %d refs (dropped %d without heat signals)",
        len(refs), len(relevant), dropped,
    )
    return relevant
