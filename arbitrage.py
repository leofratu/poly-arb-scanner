from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Final

from tradfi import get_tradfi_implied_probability

_MIN_DAYS_TO_MATURITY: Final[int] = 1
_MIN_PRICE: Final[float] = 0.001
_MAX_PRICE: Final[float] = 0.999

_DATE_FORMATS: Final[tuple[str, ...]] = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
)


@dataclass(frozen=True, slots=True)
class Opportunity:
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


def parse_end_date(date_str: str | None) -> datetime | None:
    if not date_str or not isinstance(date_str, str):
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def _extract_market_prices(
    outcomes_json: str | None,
    prices_json: str | None,
) -> tuple[list[str], list[float]] | None:
    if not outcomes_json or not prices_json:
        return None

    try:
        outcomes: list[str] = json.loads(outcomes_json)
        prices_raw: list[Any] = json.loads(prices_json)
    except (json.JSONDecodeError, TypeError):
        return None

    if not isinstance(outcomes, list) or not isinstance(prices_raw, list):
        return None

    if len(prices_raw) < 2:
        return None

    prices: list[float] = []
    for p in prices_raw:
        try:
            prices.append(float(p))
        except (TypeError, ValueError):
            return None

    if len(prices) < 2:
        return None

    return outcomes, prices


def _determine_favorite_index(outcomes: list[str], prices: list[float]) -> int:
    try:
        return outcomes.index("Yes")
    except ValueError:
        pass

    max_price = prices[0]
    max_idx = 0
    for i, p in enumerate(prices):
        if p > max_price:
            max_price = p
            max_idx = i
    return max_idx


def _is_valid_poly_prob(price: float) -> bool:
    return _MIN_PRICE < price < _MAX_PRICE


def scan_opportunities(
    events: list[dict[str, Any]],
    threshold: float,
    min_volume: float = 0.0,
    min_days: int = 1,
) -> list[Opportunity]:
    if threshold < 0:
        raise ValueError(f"Threshold cannot be negative: {threshold}")
    if min_volume < 0:
        raise ValueError(f"Min volume cannot be negative: {min_volume}")
    if min_days < 1:
        raise ValueError(f"Min days must be at least 1: {min_days}")

    now = datetime.now(timezone.utc)
    opportunities: list[Opportunity] = []

    for event in events:
        if not isinstance(event, dict):
            continue

        markets = event.get("markets", [])
        if not isinstance(markets, list):
            continue

        for market in markets:
            opp = _process_market(market, event, now, threshold, min_volume, min_days)
            if opp is not None:
                opportunities.append(opp)

    opportunities.sort(key=lambda x: x.spread, reverse=True)
    return opportunities


def _process_market(
    market: dict[str, Any],
    event: dict[str, Any],
    now: datetime,
    threshold: float,
    min_volume: float,
    min_days: int,
) -> Opportunity | None:
    if not isinstance(market, dict):
        return None

    if not market.get("active") or market.get("closed"):
        return None

    end_date_str = market.get("endDate")
    end_date = parse_end_date(end_date_str)
    if end_date is None:
        return None

    days_to_maturity = (end_date - now).days
    if days_to_maturity < min_days:
        return None

    extracted = _extract_market_prices(
        market.get("outcomes"),
        market.get("outcomePrices"),
    )
    if extracted is None:
        return None

    outcomes, prices = extracted

    yes_index = _determine_favorite_index(outcomes, prices)
    poly_prob = prices[yes_index]

    if not _is_valid_poly_prob(poly_prob):
        return None

    volume_raw = market.get("volumeNum", 0.0)
    try:
        volume = float(volume_raw if volume_raw is not None else 0.0)
    except (TypeError, ValueError):
        volume = 0.0

    if volume < min_volume:
        return None

    question = market.get("question") or event.get("title", "")
    if not question:
        return None

    if isinstance(question, str) and "TBA" in question.upper():
        return None

    tradfi_prob = get_tradfi_implied_probability(question, end_date)
    if tradfi_prob is None:
        return None

    poly_prob_pct = poly_prob * 100.0
    tradfi_prob_pct = tradfi_prob * 100.0
    spread_pct = abs(poly_prob_pct - tradfi_prob_pct)

    if spread_pct < threshold:
        return None

    favorite = outcomes[yes_index] if yes_index < len(outcomes) else "Unknown"
    market_id = market.get("id", "")

    return Opportunity(
        id=str(market_id) if market_id else "",
        question=str(question),
        end_date=str(end_date_str) if end_date_str else "",
        days=days_to_maturity,
        favorite=favorite,
        price=poly_prob,
        poly_prob=poly_prob_pct,
        tradfi_prob=tradfi_prob_pct,
        spread=spread_pct,
        volume=volume,
    )
