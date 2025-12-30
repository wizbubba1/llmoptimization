"""
CLI V2 - Multi-Model Oracle Command Line Interface

Usage:
    llm-oracle analyze BTC
    llm-oracle compare BTC ETH
    llm-oracle rank BTC,ETH,SOL,AVAX
    llm-oracle heatmap AAPL
"""

import asyncio
import argparse
import logging
import os
import sys

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llm-oracle",
        description="Multi-Model LLM Asset Oracle - AI Consensus Analysis",
    )

    parser.add_argument(
        "--models", "-m",
        type=int,
        default=15,
        help="Number of models to query (default: 15)",
    )
    parser.add_argument(
        "--budget",
        action="store_true",
        help="Use cheaper models",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Analyze
    analyze = subparsers.add_parser("analyze", help="Analyze an asset")
    analyze.add_argument("symbol", help="Asset symbol (e.g., BTC, AAPL)")
    analyze.add_argument("--heatmap", "-H", action="store_true", help="Show heatmap")

    # Compare
    compare = subparsers.add_parser("compare", help="Compare two assets")
    compare.add_argument("symbol1", help="First asset")
    compare.add_argument("symbol2", help="Second asset")

    # Rank
    rank = subparsers.add_parser("rank", help="Rank multiple assets")
    rank.add_argument("symbols", help="Comma-separated symbols (e.g., BTC,ETH,SOL)")

    # Heatmap
    heatmap = subparsers.add_parser("heatmap", help="Show model heatmap")
    heatmap.add_argument("symbol", help="Asset symbol")

    # Models
    subparsers.add_parser("models", help="List available models")

    # Bot
    subparsers.add_parser("bot", help="Run Discord bot")

    return parser


async def cmd_analyze(args):
    """Analyze an asset."""
    from llm_asset_oracle.core.multi_model_oracle import MultiModelOracle, OracleConfig
    from llm_asset_oracle.analysis.consensus_math import generate_heatmap_data, format_heatmap_text

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        return

    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=args.models,
        budget_mode=args.budget,
    )
    oracle = MultiModelOracle(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Querying {oracle.model_count} AI models...", total=None)
        result = await oracle.analyze(args.symbol.upper())

    # Direction colors
    dir_colors = {
        "STRONG_BUY": "bold green",
        "BUY": "green",
        "NEUTRAL": "yellow",
        "SELL": "red",
        "STRONG_SELL": "bold red",
    }
    color = dir_colors.get(result.direction.value, "white")

    # Header
    console.print()
    console.print(Panel(
        f"[bold]{result.symbol}[/bold] - [{color}]{result.direction.value.replace('_', ' ')}[/{color}]\n"
        f"Grade: [bold]{result.grade.value}[/bold] ({result.grade_score:.0f}/100)",
        title="🔮 Multi-Model Consensus",
    ))

    # Vote table
    table = Table(title="Model Votes")
    table.add_column("Direction", justify="center")
    table.add_column("Votes", justify="right")
    table.add_column("Percentage", justify="right")

    table.add_row("🟢 BUY", str(result.buy_votes), f"{result.buy_pct:.0f}%")
    table.add_row("🔴 SELL", str(result.sell_votes), f"{result.sell_pct:.0f}%")
    table.add_row("⚪ NEUTRAL", str(result.neutral_votes), f"{result.neutral_pct:.0f}%")

    console.print(table)

    # Metrics
    console.print()
    console.print(f"[bold]Metrics:[/bold]")
    console.print(f"  Weighted Score: {result.weighted_score:+.1f}")
    console.print(f"  Consensus Strength: {result.consensus_strength:.0f}%")
    console.print(f"  Avg Confidence: {result.avg_confidence:.0f}%")
    console.print(f"  Cost: ${result.total_cost_usd:.4f}")

    # Provider breakdown
    if result.provider_breakdown:
        console.print()
        console.print("[bold]By Provider:[/bold]")
        for provider, data in result.provider_breakdown.items():
            console.print(f"  {provider}: 🟢{data['buy']} 🔴{data['sell']} ⚪{data['neutral']}")

    # Top views
    if result.common_views:
        console.print()
        console.print("[bold]Model Views:[/bold]")
        for view in result.common_views[:3]:
            console.print(f"  • {view[:100]}")

    # Heatmap
    if args.heatmap:
        console.print()
        heatmap = format_heatmap_text(generate_heatmap_data(result))
        console.print(heatmap)

    console.print()
    console.print("[dim]⚠️  Not financial advice. Do your own research.[/dim]")


async def cmd_compare(args):
    """Compare two assets."""
    from llm_asset_oracle.core.multi_model_oracle import MultiModelOracle, OracleConfig

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        return

    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=args.models,
        budget_mode=args.budget,
    )
    oracle = MultiModelOracle(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Analyzing both assets...", total=None)
        comparison = await oracle.compare(args.symbol1.upper(), args.symbol2.upper())

    if "error" in comparison:
        console.print(f"[red]Error: {comparison['error']}[/red]")
        return

    a1, a2 = comparison["asset1"], comparison["asset2"]

    console.print()
    console.print(Panel(
        f"{args.symbol1.upper()} vs {args.symbol2.upper()}",
        title="⚖️ Comparison",
    ))

    table = Table()
    table.add_column("Metric")
    table.add_column(a1["symbol"], justify="center")
    table.add_column(a2["symbol"], justify="center")

    table.add_row("Direction", a1["direction"].replace("_", " "), a2["direction"].replace("_", " "))
    table.add_row("Grade", a1["grade"], a2["grade"])
    table.add_row("Score", f"{a1['score']:.0f}", f"{a2['score']:.0f}")
    table.add_row("Buy %", f"{a1['buy_pct']:.0f}%", f"{a2['buy_pct']:.0f}%")
    table.add_row("Sell %", f"{a1['sell_pct']:.0f}%", f"{a2['sell_pct']:.0f}%")

    console.print(table)

    console.print()
    if comparison["winner"] == "TIE":
        console.print("[yellow]Result: Too close to call[/yellow]")
    else:
        console.print(f"[bold green]Winner: {comparison['winner']}[/bold green] (+{comparison['score_diff']:.0f} pts)")


async def cmd_rank(args):
    """Rank multiple assets."""
    from llm_asset_oracle.core.multi_model_oracle import MultiModelOracle, OracleConfig

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        return

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    if len(symbols) < 2:
        console.print("[red]Provide at least 2 assets[/red]")
        return

    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=args.models,
        budget_mode=args.budget,
    )
    oracle = MultiModelOracle(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Ranking {len(symbols)} assets...", total=None)
        results = await oracle.rank_assets(symbols)

    console.print()
    console.print(Panel("Asset Ranking", title="🏆"))

    table = Table()
    table.add_column("Rank", justify="center")
    table.add_column("Symbol")
    table.add_column("Direction")
    table.add_column("Grade", justify="center")
    table.add_column("Score", justify="right")
    table.add_column("Buy/Sell", justify="center")

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for i, result in enumerate(results, 1):
        medal = medals.get(i, str(i))
        table.add_row(
            medal,
            result.symbol,
            result.direction.value.replace("_", " "),
            result.grade.value,
            f"{result.grade_score:.0f}",
            f"🟢{result.buy_pct:.0f}% 🔴{result.sell_pct:.0f}%",
        )

    console.print(table)


async def cmd_heatmap(args):
    """Show heatmap."""
    from llm_asset_oracle.core.multi_model_oracle import MultiModelOracle, OracleConfig
    from llm_asset_oracle.analysis.consensus_math import generate_heatmap_data, format_heatmap_text

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not set[/red]")
        return

    config = OracleConfig(
        openrouter_api_key=api_key,
        model_count=args.models,
        budget_mode=args.budget,
    )
    oracle = MultiModelOracle(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Generating heatmap...", total=None)
        result = await oracle.analyze(args.symbol.upper())

    heatmap = format_heatmap_text(generate_heatmap_data(result))
    console.print(heatmap)


def cmd_models(args):
    """List models."""
    from llm_asset_oracle.llm.openrouter import AVAILABLE_MODELS

    console.print()
    console.print(Panel(f"Available Models ({len(AVAILABLE_MODELS)})", title="🤖"))

    table = Table()
    table.add_column("Provider")
    table.add_column("Model")
    table.add_column("Context", justify="right")
    table.add_column("Cost (per 1K)", justify="right")

    for model in AVAILABLE_MODELS:
        cost = f"${model.cost_per_1k_input:.4f} / ${model.cost_per_1k_output:.4f}"
        table.add_row(
            model.provider,
            model.name,
            f"{model.context_length:,}",
            cost,
        )

    console.print(table)


def cmd_bot(args):
    """Run bot."""
    from llm_asset_oracle.discord_bot.new_bot import run_bot
    run_bot()


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    logging.basicConfig(level=logging.WARNING)

    try:
        if args.command == "analyze":
            asyncio.run(cmd_analyze(args))
        elif args.command == "compare":
            asyncio.run(cmd_compare(args))
        elif args.command == "rank":
            asyncio.run(cmd_rank(args))
        elif args.command == "heatmap":
            asyncio.run(cmd_heatmap(args))
        elif args.command == "models":
            cmd_models(args)
        elif args.command == "bot":
            cmd_bot(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
