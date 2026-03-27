from typing import Any

import requests_cache

session = requests_cache.CachedSession("poly_cache", expire_after=3600)


def fetch_active_events(limit: int = 50) -> list[dict[str, Any]]:
    url = f"https://gamma-api.polymarket.com/events?active=true&closed=false&limit=1000"
    response = session.get(url)
    response.raise_for_status()
    
    events = response.json()
    
    filtered_events = []
    for event in events:
        tags = event.get("tags", [])
        if any(tag.get("label") in ("Economy", "Finance") for tag in tags):
            filtered_events.append(event)
            if len(filtered_events) >= limit:
                break
                
    return filtered_events
