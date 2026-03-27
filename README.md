# PolyArb: Cross-Asset Event Arbitrage Engine

PolyArb is a quantitative CLI pipeline engineered to detect and exploit pricing dislocations between decentralized prediction markets (Polymarket) and traditional financial (TradFi) securities.

## Strategic Objective

As Polymarket scales into a major global liquidity pool, severe pricing inefficiencies persist between retail-driven prediction markets and institutional "big bank" securities. PolyArb acts as a quantitative bridge to capture these dislocations.

The engine systematically scans diverse prediction categories (macroeconomic events, weather anomalies, geopolitics, elections) and benchmarks them against correlated traditional instruments. Because prediction market prices frequently fail to accurately reflect underlying real-world probabilities, traders can utilize PolyArb to detect mispriced risk and execute cross-asset arbitrage.

## Abstract
Binary options on prediction markets frequently exhibit pricing dislocations near resolution due to retail capital inefficiency and liquidity fragmentation. By modeling high-probability `Yes` contracts as zero-coupon bonds, PolyArb identifies synthetic fixed-income instruments that out-yield the traditional risk-free rate ($R_f$).

## Quantitative Framework

### 1. Decentralized Implied Probability
A binary contract pays 1.00 USDC at $T$ if event $E$ occurs. Let $P$ be the current limit ask price for the `Yes` outcome. The decentralized market-implied probability is:
```math
P_{poly} = P
```

### 2. Institutional Implied Probability (Black-Scholes)
To benchmark the decentralized probability against traditional finance (TradFi), the engine parses the underlying asset spot price $S$, the event strike price $K$, and time to maturity $T_{years}$.

Using the Black-Scholes options pricing model, the risk-neutral probability of the asset closing in-the-money (ITM) is the cumulative distribution function $\Phi$ evaluated at $d_2$:
```math
d_2 = \frac{\ln(S/K) + (R_f - \frac{\sigma_{iv}^2}{2})T_{years}}{\sigma_{iv}\sqrt{T_{years}}}
```
```math
P_{tradfi} = \Phi(d_2)
```
Where $\sigma_{iv}$ is the implied volatility derived from the closest active options chain.

### 3. Spread Calculation
We construct a continuous risk-free yield curve $R_f$ via linear interpolation of US Treasury active contracts (`^IRX`, `^FVX`, `^TNX`). The actionable cross-asset spread $\sigma_{arb}$ is defined as the absolute divergence between the two probabilities:
```math
\sigma_{arb} = |P_{poly} - P_{tradfi}|
```

An arbitrage signal is generated when $\sigma_{arb} > \sigma_{threshold}$, subject to liquidity constraints.

### 4. Assumptions & Risks
* **Counterparty Risk**: Assumes zero protocol exploit risk (Polymarket/UMA Oracle).
* **Currency Risk**: Assumes USDC maintains strict 1:1 USD peg until $T$.
* **Data Limitations**: The engine requires liquid options chains via Yahoo Finance. Weather derivatives (e.g., CME HDD/CDD futures) lack free institutional options data and will be bypassed.
* **Execution**: PolyArb scans top-of-book (BBO). Deep fills require volume-weighted average price (VWAP) adjustments.

## System Architecture
* **Data Ingestion (ETL)**: Synchronous polling of the Polymarket Gamma API and Yahoo Finance.
* **Persistence**: SQLite-backed caching to minimize API rate-limit exhaustion.
* **Agentic NLP Interface**: Integrates `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter to parse complex market criteria and execute natural language filtering over the spread matrix.

## Deployment

Requires `uv` for dependency resolution.
```bash
uv sync
```

## Execution Pipeline

### Terminal Scanner
Execute a cross-market scan targeting a minimum annualized spread $\sigma \ge 5.0$ percent:
```bash
uv run python main.py scan --threshold 5.0
```

Export quantitative parameter arrays to CSV/JSON for backtesting or automated execution modules:
```bash
uv run python main.py scan --threshold 3.0 --export csv
```

### Agentic Matrix Query
Launch the Nvidia Nemotron LLM to query the cached arbitrage matrix:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
uv run python main.py chat
```
