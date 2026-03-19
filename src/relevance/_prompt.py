"""Shared relevance-check prompt for LLM providers."""

SYSTEM_PROMPT = (
    "You are a news classifier. Determine if an article is about "
    "HEAT or HEATWAVE impact in a SPECIFIC REGION of INDIA. "
    "Answer ONLY 'Yes' or 'No'."
)

USER_PROMPT_TEMPLATE = """\
RELEVANT (Yes):
- Heatwave or extreme heat events in {state} (or {district} if given)
- Temperature records or forecasts showing unusual heat in {state}
- Heat-related health issues (heatstroke, heat deaths, dehydration) in {state}
- Heat-caused infrastructure problems (power outages, water shortages) in {state}
- Government heat advisories, IMD warnings, or red/orange alerts for {state}
- National-level or multi-state heat news that covers {state} or the region it belongs to
- Weather forecasts that discuss heat, rising temperatures, or hot conditions in {state}
- Articles about rain or storms that discuss relief FROM HEAT or end of a heat spell in {state}
- Articles mentioning broad Indian regions that INCLUDE {state} (e.g. "Indo-Gangetic Plains", "North India", "South India", "central India", "eastern India", river basins like "Ganga belt", "Yamuna belt", "Godavari basin", "Cauvery basin", Deccan Plateau, Vidarbha, Marathwada, Telangana Plateau, Konkan, Coastal Andhra, etc.)

NOT RELEVANT (No):
- Heat news ONLY about a different Indian state with no connection to {state} (e.g. "Delhi records 47°C" when target is Kerala — answer No. But "North India heatwave" when target is Bihar — answer Yes because Bihar is in North India)
- Heat news from outside India (USA, Pakistan, Middle East, etc.) with no mention of {state} or India
- Weather articles about rain, cold, fog, or storms with NO mention of heat or temperatures
- Products, entertainment, or sports mentioning "heat"
- Articles where heat/temperature is mentioned only incidentally

State: {state}
District: {district}
Title: {title}
Content (first 500 chars): {text_preview}

Answer ONLY "Yes" or "No"."""


def build_prompt(
    title: str,
    full_text: str | None,
    state: str = "",
    district: str | None = None,
) -> str:
    """Build the user prompt from article title, text, and geographic context."""
    preview = ""
    if full_text:
        preview = full_text[:500].strip()
    return USER_PROMPT_TEMPLATE.format(
        title=title,
        text_preview=preview or "(no text)",
        state=state or "(unknown)",
        district=district or "(not specified)",
    )
