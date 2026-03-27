# Poly-Arb-Scanner

A quantitative terminal interface designed to detect duration-mismatched yield spreads between prediction markets (Polymarket) and traditional fixed-income benchmark rates (US Treasuries).

## Theoretical Framework

The core arbitrage engine models binary options on prediction markets against the risk-free rate of return to identify mispriced capital allocation opportunities.

### Yield Calculation

For a binary outcome contract pricing the favorite at $P_{fav} \in (0, 1)$, the absolute return $R_{poly}$ holding to resolution $T$ (assuming outcome realization) is:

$$
R_{poly} = \frac{1 - P_{fav}}{P_{fav}}
$$

To standardize against traditional instruments, we calculate the annualized yield $Y_{poly}$ over the remaining duration $D$ in days:

$$
Y_{poly} = R_{poly} \times \left( \frac{365}{D} \right)
$$

### Spread Derivation

We interpolate the risk-free rate $R_{rf}$ for duration $D$ using live US Treasury yields (`^IRX`, `^FVX`, `^TNX`). The executable spread $S$ is defined as:

$$
S = Y_{poly} - R_{rf}(D)
$$

An opportunity is flagged when $S > \tau$, where $\tau$ is a user-defined minimum profit margin threshold.

## Features

* **Order Book Ingestion**: Fetches active Polymarket events, parsing CLOB metrics and outcome pricing via the Gamma API.
* **Dynamic Curve Interpolation**: Generates continuous risk-free rate approximations matched to exact contract maturities using `yfinance`.
* **Agentic Market Analysis**: Integrates `nvidia/nemotron-3-super-120b-a12b:free` via OpenRouter to analyze live spreads and process natural language queries.
* **Quantitative CLI**: OpenCode-inspired terminal UI with stylized data tables and pipeline exports (CSV, JSON).

## Installation

Ensure you have the `uv` package manager installed.

```bash
uv sync
```

## CLI Usage

### Market Scanner
Detect arbitrage setups exceeding a specific annualized spread threshold:
```bash
uv run python main.py scan --threshold 5.0
```

Dump identified parameters to disk for downstream pipeline ingestion:
```bash
uv run python main.py scan --threshold 3.0 --export csv
```

### Agentic Chat
Interact with the quantitative dataset via the integrated Nvidia Nemotron model:
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
uv run python main.py chat
```
