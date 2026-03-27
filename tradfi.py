import math
import re
from datetime import datetime, timezone
from typing import Final, Tuple

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


def norm_cdf(x: float) -> float:
    """Basic normal cumulative distribution function."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def calculate_implied_probability(
    S: float, K: float, T_years: float, r: float, sigma: float
) -> float:
    """Calculate the Black-Scholes implied probability N(d2) of finishing ITM."""
    if T_years <= 0 or sigma <= 0:
        return 1.0 if S >= K else 0.0
    d2 = (math.log(S / K) + (r - 0.5 * sigma**2) * T_years) / (sigma * math.sqrt(T_years))
    return norm_cdf(d2)


def extract_financial_target(question: str) -> Tuple[str, float, bool] | None:
    """Parse a Polymarket question to extract a ticker, target price, and direction."""
    tickers_pattern = r"\b(SPY|QQQ|AAPL|TSLA|NVDA|BTC|ETH|MSTR|COIN)\b"
    ticker_match = re.search(tickers_pattern, question, re.IGNORECASE)
    if not ticker_match:
        return None

    ticker = ticker_match.group(1).upper()
    if ticker == "BTC":
        ticker = "BTC-USD"
    if ticker == "ETH":
        ticker = "ETH-USD"

    # Match numeric target with optional commas and k/m suffixes
    price_match = re.search(r"\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*([kKmM]?)", question)
    if not price_match:
        return None

    price_str = price_match.group(1).replace(",", "")
    try:
        price = float(price_str)
    except ValueError:
        return None

    suffix = price_match.group(2).lower()
    if suffix == "k":
        price *= 1000.0
    elif suffix == "m":
        price *= 1000000.0

    # Direction: above (default) vs below
    is_above = True
    if re.search(r"\b(below|under|lower|less|crash)\b", question, re.IGNORECASE):
        is_above = False

    return ticker, price, is_above


def get_tradfi_implied_probability(
    question: str, target_date: datetime
) -> float | None:
    """
    Given a Polymarket question, attempt to derive a TradFi options-based implied probability.
    Returns None if no ticker match or data is unavailable.
    """
    parsed = extract_financial_target(question)
    if not parsed:
        return None

    ticker, target_price, is_above = parsed

    try:
        t = yf.Ticker(ticker)
        current_price = t.fast_info.last_price
        if current_price is None or current_price == 0:
            return None

        options = t.options
        if not options:
            return None

        # Find closest expiration date on or after target_date
        best_exp = None
        min_diff = float("inf")
        for exp_str in options:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            diff = (exp_date - target_date).days
            if 0 <= diff < min_diff:
                min_diff = diff
                best_exp = exp_str

        if not best_exp:
            best_exp = options[-1]

        chain = t.option_chain(best_exp)

        # ATM IV is usually similar for puts/calls, we use calls here to get a general volatility
        calls = chain.calls
        if calls.empty:
            return None

        # Get IV from the option closest to the target strike
        closest_call = calls.iloc[(calls["strike"] - target_price).abs().argsort()[:1]]
        if closest_call.empty:
            return None

        sigma = float(closest_call["impliedVolatility"].values[0])
        if sigma < 0.01:
            sigma = 0.3  # fallback if illiquid

        # We assume target_date is the expiration for the probability math
        days_to_maturity = max(1, (target_date - datetime.now(timezone.utc)).days)
        T_years = days_to_maturity / 365.25
        r = get_risk_free_rate(days_to_maturity) / 100.0

        prob_above = calculate_implied_probability(
            current_price, target_price, T_years, r, sigma
        )

        return prob_above if is_above else max(0.0, 1.0 - prob_above)

    except Exception:
        return None
