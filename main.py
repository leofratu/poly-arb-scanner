import csv
import json
import os
from typing import Literal

import requests
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.markdown import Markdown

from arbitrage import Opportunity, scan_opportunities
from polymarket import fetch_active_events

app = typer.Typer(help="poly-arb-scanner CLI")
console = Console()

BANNER = """[bold cyan]
 ╔══════════════════════════════════════════════════════════╗
 ║  [bold white]P O L Y - A R B - S C A N N E R[/bold white]                         ║
 ║  [dim]Terminal Dashboard & AI Arbitrage Engine[/dim]                ║
 ╚══════════════════════════════════════════════════════════╝
[/bold cyan]"""

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
    console.print(f"\\n[bold green]✓[/bold green] Exported {len(data)} opportunities to [bold white]{filename}[/bold white]")

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
    """Scan Polymarket for risk-adjusted arbitrage opportunities."""
    console.print(BANNER)
    
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
        console.print(Panel("[bold yellow]No opportunities found exceeding the threshold.[/bold yellow]", border_style="yellow"))
        return

    table = Table(show_header=True, header_style="bold magenta", border_style="cyan", title_justify="left")
    table.title = f"\\n[bold white]Arbitrage Opportunities (>{threshold}% Spread)[/bold white]"
    table.add_column("Market", style="cyan", no_wrap=False, max_width=45)
    table.add_column("Days", justify="right", style="magenta")
    table.add_column("Favorite", style="blue")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Poly Yield", justify="right")
    table.add_column("TradFi", justify="right", style="dim")
    table.add_column("Spread", justify="right", style="bold red")

    for opp in opportunities[:20]:
        question = opp["question"]
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

@app.command()
def chat(
    limit: int = typer.Option(50, "--limit", "-l", help="Number of events to analyze"),
    threshold: float = typer.Option(1.0, "--threshold", "-t", help="Minimum spread to feed to AI"),
) -> None:
    """Chat with an AI assistant about current arbitrage opportunities."""
    console.print(BANNER)
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        console.print(Panel("[bold yellow]Missing OPENROUTER_API_KEY[/bold yellow]\\n\\nPlease set your OpenRouter API key to use the AI chat feature:\\n[dim]export OPENROUTER_API_KEY='sk-or-v1-...'[/dim]\\n\\nIf you don't have one, get it at [underline]https://openrouter.ai/[/underline]", border_style="yellow"))
        
        # Create a .env file as a placeholder if it doesn't exist
        if not os.path.exists(".env"):
            with open(".env", "w") as f:
                f.write("OPENROUTER_API_KEY=your_key_here\n")
            console.print("[dim]A placeholder .env file has been created in the current directory.[/dim]")
            
        raise typer.Exit(1)
        
    with console.status("[bold green]Gathering live market data for AI context..."):
        try:
            events = fetch_active_events(limit)
            opportunities = scan_opportunities(events, threshold)
            
            # Compress data to save tokens
            compressed_opps = []
            for opp in opportunities[:30]:
                compressed_opps.append({
                    "q": opp["question"],
                    "days": opp["days"],
                    "fav": opp["favorite"],
                    "p": opp["price"],
                    "spread": round(opp["spread"], 2)
                })
            context_data = json.dumps(compressed_opps)
        except Exception as e:
            console.print(f"[bold red]Error gathering data: {e}")
            raise typer.Exit(code=1)

    console.print("[bold green]✓[/bold green] Live market data loaded. You are now chatting with the Poly-Arb AI (powered by OpenRouter Free Models).\\n")
    
    messages = [
        {
            "role": "system",
            "content": f"You are a Polymarket arbitrage analyst. You help the user find the best trading opportunities based on live data. Here are the top live opportunities right now (spread is Polymarket annualized yield minus risk-free TradFi yield): {context_data}. Be extremely concise, use bullet points, and highlight the highest spreads. Do not invent data."
        }
    ]
    
    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
            if user_input.lower() in ["exit", "quit", "q"]:
                break
                
            messages.append({"role": "user", "content": user_input})
            
            with console.status("[bold magenta]AI is thinking..."):
                response = requests.post(
                    url="https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
                        "messages": messages
                    }
                )
                
            if response.status_code != 200:
                console.print(f"[bold red]API Error:[/bold red] {response.text}")
                messages.pop() # remove failed message
                continue
                
            data = response.json()
            ai_msg = data["choices"][0]["message"]["content"]
            messages.append({"role": "assistant", "content": ai_msg})
            
            console.print(Panel(Markdown(ai_msg), title="[bold magenta]Poly-Arb AI[/bold magenta]", border_style="magenta", padding=(1, 2)))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()
