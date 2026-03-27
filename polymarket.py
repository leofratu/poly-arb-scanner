from typing import Any

import requests_cache

session = requests_cache.CachedSession("poly_cache", expire_after=3600)


def fetch_active_events(limit: int = 50) -> list[dict[str, Any]]:
    url = f"https://gamma-api.polymarket.com/events?active=true&closed=false&limit={limit}"
    response = session.get(url)
    response.raise_for_status()
    return response.json()
