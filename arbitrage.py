import json
from datetime import datetime, timezone
from typing import TypedDict

from tradfi import get_tradfi_implied_probability


class Opportunity(TypedDict):
    id: str
    question: str
    end_date: str
    days: int
    favorite: str
    price: float
    poly_prob: float
    tradfi_prob: float
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

            # Focus on 'Yes' outcome. The question is usually binary Yes/No
            try:
                yes_index = outcomes.index("Yes")
            except ValueError:
                # Fallback: choose the favorite
                yes_index = prices.index(max(prices))

            poly_prob = prices[yes_index]
            if poly_prob <= 0.0 or poly_prob >= 1.0:
                continue

            # Rebuild spread using TradFi probabilities
            question = market.get("question", event.get("title", ""))
            tradfi_prob = get_tradfi_implied_probability(question, end_date)

            if tradfi_prob is None:
                continue

            poly_prob_pct = poly_prob * 100.0
            tradfi_prob_pct = tradfi_prob * 100.0
            spread_pct = abs(poly_prob_pct - tradfi_prob_pct)

            if spread_pct < threshold:
                continue

            opp: Opportunity = {
                "id": market.get("id", ""),
                "question": question,
                "end_date": end_date_str,
                "days": days_to_maturity,
                "favorite": outcomes[yes_index] if yes_index < len(outcomes) else "Yes",
                "price": poly_prob,
                "poly_prob": poly_prob_pct,
                "tradfi_prob": tradfi_prob_pct,
                "spread": spread_pct,
                "volume": float(market.get("volumeNum", 0.0) or 0.0),
            }
            opportunities.append(opp)

    opportunities.sort(key=lambda x: x["spread"], reverse=True)
    return opportunities
