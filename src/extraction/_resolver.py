"""Google News URL resolver.

Resolves ``news.google.com`` redirect URLs to actual article URLs using
two strategies: (1) HTTP redirect following, (2) batchexecute endpoint
decoding.  Non-Google URLs pass through unchanged.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import quote, urlparse

import httpx
from lxml import html as lxml_html

logger = logging.getLogger(__name__)


async def _get_decoding_params(
    gn_art_id: str, client: httpx.AsyncClient
) -> dict[str, str] | None:
    """Fetch signature and timestamp needed for batchexecute decoding.

    Loads the Google News article page and extracts ``data-n-a-sg``
    (signature) and ``data-n-a-ts`` (timestamp) attributes from the
    first ``c-wiz > div`` element.
    """
    try:
        response = await client.get(
            f"https://news.google.com/rss/articles/{gn_art_id}",
            timeout=10.0,
        )
        response.raise_for_status()
        tree = lxml_html.fromstring(response.text)
        # Use XPath instead of cssselect to avoid cssselect import issues
        divs = tree.xpath("//c-wiz/div")
        if not divs:
            logger.debug("No c-wiz/div element found for article %s", gn_art_id)
            return None
        return {
            "signature": divs[0].get("data-n-a-sg", ""),
            "timestamp": divs[0].get("data-n-a-ts", ""),
            "gn_art_id": gn_art_id,
        }
    except Exception:
        logger.debug(
            "Failed to get decoding params for %s", gn_art_id, exc_info=True
        )
        return None


async def _decode_via_batchexecute(
    url: str, client: httpx.AsyncClient
) -> str | None:
    """Decode a Google News URL via Google's batchexecute endpoint.

    Extracts the article ID from *url*, fetches decoding parameters
    (signature + timestamp), then POSTs to batchexecute to obtain the
    actual article URL.
    """
    gn_art_id = urlparse(url).path.split("/")[-1]
    params = await _get_decoding_params(gn_art_id, client)
    if not params:
        return None

    payload_inner = (
        f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",'
        f'null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,'
        f'null,0,0,null,0],"{params["gn_art_id"]}",'
        f'{params["timestamp"]},"{params["signature"]}"]'
    )
    payload = f"f.req={quote(json.dumps([[['Fbv4je', payload_inner]]]))})"

    try:
        response = await client.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            content=payload,
            headers={
                "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            },
            timeout=10.0,
        )
        response.raise_for_status()
        parts = response.text.split("\n\n", 1)
        if len(parts) < 2:
            logger.debug("batchexecute response missing boundary for %s", url)
            return None
        data = json.loads(parts[1])
        decoded_url: str = json.loads(data[0][2])[1]
        logger.debug("batchexecute resolved %s -> %s", url, decoded_url)
        return decoded_url
    except Exception:
        logger.debug("batchexecute decoding failed for %s", url, exc_info=True)
        return None


async def resolve_url(url: str, client: httpx.AsyncClient) -> str:
    """Resolve a URL to the actual article URL.

    For non-Google URLs the input is returned unchanged.  For Google News
    redirect URLs, two strategies are tried in order:

    1. **HTTP redirect following** -- fastest path, works when Google
       issues a standard 3xx redirect.
    2. **batchexecute decoding** -- fallback for URLs that don't redirect
       (newer ``AU_yqL``-style article IDs).

    Returns the original URL if all strategies fail (graceful degradation).
    Never raises.
    """
    if "news.google.com" not in url:
        return url

    # Strategy 1: Follow HTTP redirects
    try:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        final_url = str(response.url)
        if "news.google.com" not in final_url:
            logger.debug("Redirect resolved %s -> %s", url, final_url)
            return final_url
    except httpx.HTTPError as exc:
        logger.debug("Redirect strategy failed for %s: %s", url, exc)
    except Exception:
        logger.debug("Redirect strategy error for %s", url, exc_info=True)

    # Strategy 2: batchexecute decoding
    try:
        resolved = await _decode_via_batchexecute(url, client)
        if resolved:
            return resolved
    except Exception:
        logger.debug("batchexecute strategy error for %s", url, exc_info=True)

    logger.warning("Could not resolve Google News URL: %s", url)
    return url
