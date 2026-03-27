from typing import Final

import yfinance as yf

_YIELD_CURVE_CACHE: dict[int, float] = {}

FALLBACK_YIELDS: Final[dict[int, float]] = {90: 4.5, 5 * 365: 4.0, 10 * 365: 4.2}
TICKER_DAYS: Final[dict[str, int]] = {"^IRX": 90, "^FVX": 5 * 365, "^TNX": 10 * 365}


def get_yield_curve() -> dict[int, float]:
    if _YIELD_CURVE_CACHE:
        return _YIELD_CURVE_CACHE

    curve: dict[int, float] = {}
    for ticker, days in TICKER_DAYS.items():
        try:
            price = yf.Ticker(ticker).fast_info.last_price
            if price is not None:
                curve[days] = float(price)
        except Exception:
            continue

    if not curve:
        curve = FALLBACK_YIELDS.copy()

    _YIELD_CURVE_CACHE.update(curve)
    return _YIELD_CURVE_CACHE


def get_risk_free_rate(days_to_maturity: int) -> float:
    curve = get_yield_curve()
    points = sorted(curve.items())

    if days_to_maturity <= points[0][0]:
        return points[0][1]
    if days_to_maturity >= points[-1][0]:
        return points[-1][1]

    for i in range(len(points) - 1):
        d1, y1 = points[i]
        d2, y2 = points[i + 1]
        if d1 <= days_to_maturity <= d2:
            fraction = (days_to_maturity - d1) / (d2 - d1)
            return y1 + fraction * (y2 - y1)

    return points[-1][1]
