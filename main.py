import csv
import json
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table

from arbitrage import Opportunity, scan_opportunities
from polymarket import fetch_active_events

app = typer.Typer(help="poly-arb-scanner CLI")
console = Console()


def export_data(data: list[Opportunity], format_type: Literal["json", "csv"]) -> None:
    filename = f"arbitrage_opportunities.{format_type}"
    if format_type == "json":
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
    else:
        with open(filename, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    console.print(f"[bold green]Exported to {filename}")


@app.command()
def scan(
    threshold: float = typer.Option(
        5.0, "--threshold", "-t", help="Minimum profit margin threshold (%)"
    ),
    export: str = typer.Option(
        None, "--export", "-e", help="Export format: csv or json"
    ),
    limit: int = typer.Option(
        50, "--limit", "-l", help="Number of Polymarket events to fetch"
    ),
) -> None:
    with console.status(
        f"[bold green]Fetching {limit} active Polymarket events..."
    ) as status:
        try:
            events = fetch_active_events(limit)
            status.update(
                "[bold cyan]Analyzing markets and comparing with TradFi yields..."
            )
            opportunities = scan_opportunities(events, threshold)
        except Exception as e:
            console.print(f"[bold red]Error during scanning: {e}")
            raise typer.Exit(code=1)

    if not opportunities:
        console.print("[bold yellow]No opportunities found exceeding the threshold.")
        return

    table = Table(title=f"Polymarket Arbitrage Opportunities (>{threshold}% Spread)")
    table.add_column("Market", style="cyan", no_wrap=True)
    table.add_column("Days", justify="right", style="magenta")
    table.add_column("Favorite", style="blue")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Poly Yield", justify="right")
    table.add_column("TradFi Yield", justify="right")
    table.add_column("Spread", justify="right", style="bold red")

    for opp in opportunities[:20]:
        question = opp["question"][:50] + ("..." if len(opp["question"]) > 50 else "")
        table.add_row(
            question,
            str(opp["days"]),
            opp["favorite"],
            f"${opp['price']:.3f}",
            f"{opp['poly_yield']:.1f}%",
            f"{opp['tradfi_yield']:.1f}%",
            f"{opp['spread']:.1f}%",
        )

    console.print(table)

    if len(opportunities) > 20:
        console.print(f"[dim]Showing 20 of {len(opportunities)} opportunities.[/dim]")

    if export and export.lower() in ("json", "csv"):
        export_data(opportunities, export.lower())  # type: ignore
    elif export:
        console.print(f"[bold red]Unsupported export format: {export}")


if __name__ == "__main__":
    app()
