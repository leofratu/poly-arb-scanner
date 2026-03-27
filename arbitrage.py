from datetime import datetime, timezone
from typing import TypedDict
import json

from tradfi import get_risk_free_rate


class Opportunity(TypedDict):
    id: str
    question: str
    end_date: str
    days: int
    favorite: str
    price: float
    poly_yield: float
    tradfi_yield: float
    spread: float
    volume: float


def parse_end_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def scan_opportunities(events: list[dict], threshold: float) -> list[Opportunity]:
    now = datetime.now(timezone.utc)
    opportunities: list[Opportunity] = []

    for event in events:
        for market in event.get("markets", []):
            if not market.get("active") or market.get("closed"):
                continue

            end_date_str = market.get("endDate")
            if not end_date_str:
                continue

            end_date = parse_end_date(end_date_str)
            if not end_date:
                continue

            days_to_maturity = (end_date - now).days
            if days_to_maturity <= 0:
                continue

            try:
                outcomes = json.loads(market.get("outcomes", "[]"))
                prices = [
                    float(p) for p in json.loads(market.get("outcomePrices", "[]"))
                ]
            except (json.JSONDecodeError, ValueError, TypeError):
                continue

            if len(prices) != 2:
                continue

            max_price = max(prices)
            if max_price <= 0 or max_price >= 1:
                continue

            raw_return = (1.0 - max_price) / max_price
            annualized_return_pct = raw_return * (365.0 / days_to_maturity) * 100.0
            rfr = get_risk_free_rate(days_to_maturity)
            spread_pct = annualized_return_pct - rfr

            if spread_pct < threshold:
                continue

            favorite_idx = prices.index(max_price)
            opp: Opportunity = {
                "id": market.get("id", ""),
                "question": market.get("question", ""),
                "end_date": end_date_str,
                "days": days_to_maturity,
                "favorite": outcomes[favorite_idx]
                if favorite_idx < len(outcomes)
                else f"{max_price:.2f}",
                "price": max_price,
                "poly_yield": annualized_return_pct,
                "tradfi_yield": rfr,
                "spread": spread_pct,
                "volume": float(market.get("volumeNum", 0.0) or 0.0),
            }
            opportunities.append(opp)

    opportunities.sort(key=lambda x: x["spread"], reverse=True)
    return opportunities
