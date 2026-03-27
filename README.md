# PolyArb: Cross-Asset Event Arbitrage Engine

PolyArb is a quantitative CLI pipeline engineered to detect and exploit pricing dislocations between decentralized prediction markets (Polymarket) and traditional financial (TradFi) securities.

## Strategic Objective

As Polymarket scales into a major global liquidity pool, severe pricing inefficiencies persist between retail-driven prediction markets and institutional "big bank" securities. PolyArb acts as a quantitative bridge to capture these dislocations.

The engine systematically scans diverse prediction categories (macroeconomic events, weather anomalies, geopolitics, elections) and benchmarks them against correlated traditional instruments. Because prediction market prices frequently fail to accurately reflect underlying real-world probabilities, traders can utilize PolyArb to detect mispriced risk and execute cross-asset arbitrage.

## Abstract
Binary options on prediction markets frequently exhibit pricing dislocations near resolution due to retail capital inefficiency and liquidity fragmentation. By modeling high-probability `Yes` contracts as zero-coupon bonds, PolyArb identifies synthetic fixed-income instruments that out-yield the traditional risk-free rate ($R_f$).

## Quantitative Framework

### 1. Risk-Neutral Pricing Model
A binary contract pays 1.00 USDC at $T$ if event $E$ occurs. Let $P$ be the current limit ask price for the `Yes` outcome. The market-implied probability is $p = P$.

Assuming $E$ is a near-certainty ($p \to 1$), purchasing the contract at $P$ yields an absolute return $R$:
```math
R = \frac{1 - P}{P}
```

### 2. Duration Standardization (APY)
To benchmark against TradFi instruments, we annualize the return over the time to maturity $\Delta t = T - t$ (in days):
```math
Y_{poly} = R \times \left( \frac{365}{\Delta t} \right)
```

### 3. Spread Calculation
We construct a continuous risk-free yield curve $R_f(\tau)$ via linear interpolation of US Treasury active contracts (`^IRX`, `^FVX`, `^TNX`). The actionable spread $\sigma$ is defined as:
```math
\sigma = Y_{poly} - R_f(\Delta t)
```

An arbitrage signal is generated when $\sigma > \sigma_{threshold}$, subject to liquidity constraints.

### 4. Assumptions & Risks
* **Counterparty Risk**: Assumes zero protocol exploit risk (Polymarket/UMA Oracle).
* **Currency Risk**: Assumes USDC maintains strict 1:1 USD peg until $T$.
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
