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
- National-level heat news that explicitly mentions {state}
- Weather forecasts that discuss heat, rising temperatures, or hot conditions in {state}
- Articles about rain or storms that discuss relief FROM HEAT or end of a heat spell in {state}

NOT RELEVANT (No):
- Heat news about a DIFFERENT Indian state (if the title names another state like "Delhi heatwave" but the target state is Bihar, answer No)
- Heat news from outside India (e.g. USA, Pakistan, unless it also covers {state})
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
