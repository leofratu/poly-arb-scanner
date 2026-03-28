from __future__ import annotations

from typing import Any, Final

import requests
import requests_cache

_POLYMARKET_API_URL: Final[str] = "https://gamma-api.polymarket.com/events"
_DEFAULT_EXPIRE_AFTER: Final[int] = 3600
_DEFAULT_LIMIT: Final[int] = 1000

VALID_TAGS: Final[frozenset[str]] = frozenset({"Economy", "Finance", "Crypto"})

_session = requests_cache.CachedSession(
    "poly_cache",
    expire_after=_DEFAULT_EXPIRE_AFTER,
)


class PolymarketAPIError(Exception):
    pass


class PolymarketConnectionError(PolymarketAPIError):
    pass


class PolymarketResponseError(PolymarketAPIError):
    pass


def _validate_event(event: dict[str, Any]) -> bool:
    if not isinstance(event, dict):
        return False

    tags = event.get("tags", [])
    if not isinstance(tags, list):
        return False

    for tag in tags:
        if not isinstance(tag, dict):
            continue
        label = tag.get("label")
        if isinstance(label, str) and label in VALID_TAGS:
            return True

    return False


def fetch_active_events(limit: int = 50) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError(f"Limit must be positive, got {limit}")

    params = {
        "active": "true",
        "closed": "false",
        "limit": str(_DEFAULT_LIMIT),
    }

    try:
        response = _session.get(_POLYMARKET_API_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise PolymarketConnectionError(
            f"Failed to connect to Polymarket API: {e}"
        ) from e
    except requests.exceptions.Timeout as e:
        raise PolymarketConnectionError(f"Polymarket API request timed out: {e}") from e
    except requests.exceptions.HTTPError as e:
        raise PolymarketResponseError(f"Polymarket API returned error: {e}") from e
    except requests.exceptions.RequestException as e:
        raise PolymarketAPIError(f"Polymarket API request failed: {e}") from e

    try:
        events = response.json()
    except ValueError as e:
        raise PolymarketResponseError(
            f"Failed to parse Polymarket API response: {e}"
        ) from e

    if not isinstance(events, list):
        raise PolymarketResponseError("Polymarket API returned non-list response")

    filtered_events: list[dict[str, Any]] = []
    for event in events:
        if _validate_event(event):
            filtered_events.append(event)
            if len(filtered_events) >= limit:
                break

    return filtered_events
