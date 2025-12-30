"""Command-line interface for LLM Asset Oracle."""

import asyncio
import argparse
import logging
import sys
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from llm_asset_oracle.core.oracle import LLMAssetOracle
from llm_asset_oracle.core.config import get_settings


console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="llm-oracle",
        description="LLM Asset Oracle - AI-powered multi-model asset analysis",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze an asset")
    analyze_parser.add_argument("symbol", help="Asset symbol (e.g., BTC, AAPL)")
    analyze_parser.add_argument(
        "--detailed", "-d", action="store_true", help="Show detailed breakdown"
    )
    analyze_parser.add_argument(
        "--no-cache", action="store_true", help="Bypass cache and query fresh"
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare two assets")
    compare_parser.add_argument("symbol1", help="First asset symbol")
    compare_parser.add_argument("symbol2", help="Second asset symbol")

    # Top command
    top_parser = subparsers.add_parser("top", help="Get top-rated assets")
    top_parser.add_argument(
        "--category",
        "-c",
        choices=["crypto", "stock", "all"],
        default="all",
        help="Asset category",
    )
    top_parser.add_argument(
        "--limit", "-n", type=int, default=10, help="Number of results"
    )

    # Status command
    subparsers.add_parser("status", help="Show Oracle status")

    # Bot command
    subparsers.add_parser("bot", help="Run Discord bot")

    return parser


async def cmd_analyze(args):
    """Handle analyze command."""
    oracle = LLMAssetOracle()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(f"Analyzing {args.symbol.upper()}...", total=None)
        await oracle.initialize()
        result = await oracle.analyze(
            args.symbol.upper(),
            use_cache=not args.no_cache,
        )

    consensus = result.consensus
    asset = consensus.asset

    # Header
    rec_colors = {
        "STRONG BUY": "green",
        "BUY": "green",
        "HOLD": "yellow",
        "SELL": "red",
        "STRONG SELL": "red",
    }
    color = rec_colors.get(consensus.recommendation, "white")

    console.print()
    console.print(
        Panel(
            f"[bold]{asset.name}[/bold] ({asset.symbol})\n"
            f"[{color}]{consensus.recommendation}[/{color}]",
            title="🔮 LLM Asset Oracle",
        )
    )

    # Main scores
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("LOS Score", f"[bold]{consensus.los_score:.1f}[/bold]/100")
    table.add_row("Consensus Strength", f"{consensus.consensus_strength:.0f}%")
    table.add_row(
        "Confidence Interval",
        f"{consensus.confidence_interval[0]:.1f} - {consensus.confidence_interval[1]:.1f}",
    )
    table.add_row(
        "Model Votes",
        f"🟢 {consensus.bullish_models} | ⚪ {consensus.neutral_models} | 🔴 {consensus.bearish_models}",
    )

    console.print(table)

    # Market data if available
    if result.market_data and result.market_data.get("price"):
        console.print()
        console.print("[bold]Market Data[/bold]")
        md = result.market_data
        change = md.get("change_24h", 0)
        change_color = "green" if change >= 0 else "red"
        console.print(f"  Price: ${md['price']:,.2f}")
        console.print(f"  24h Change: [{change_color}]{change:+.2f}%[/{change_color}]")
        if md.get("market_cap"):
            console.print(f"  Market Cap: ${md['market_cap']:,.0f}")

    # Detailed breakdown
    if args.detailed:
        console.print()
        console.print("[bold]Model Breakdown[/bold]")

        model_table = Table(show_header=True)
        model_table.add_column("Provider")
        model_table.add_column("Model")
        model_table.add_column("Overall", justify="right")
        model_table.add_column("Risk", justify="right")
        model_table.add_column("Latency", justify="right")

        for response in consensus.responses:
            model_table.add_row(
                response.provider,
                response.model[:30],
                f"{response.rating.overall_score:.1f}",
                f"{response.rating.risk_score:.1f}",
                f"{response.latency_ms:.0f}ms",
            )

        console.print(model_table)

        # Factors
        if consensus.common_bullish_factors:
            console.print()
            console.print("[bold green]Bullish Factors[/bold green]")
            for factor in consensus.common_bullish_factors[:5]:
                console.print(f"  • {factor}")

        if consensus.common_bearish_factors:
            console.print()
            console.print("[bold red]Risk Factors[/bold red]")
            for factor in consensus.common_bearish_factors[:5]:
                console.print(f"  • {factor}")

    # Disclaimer
    console.print()
    console.print(
        "[dim]⚠️  This is not financial advice. Do your own research.[/dim]"
    )


async def cmd_compare(args):
    """Handle compare command."""
    oracle = LLMAssetOracle()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(
            f"Comparing {args.symbol1.upper()} vs {args.symbol2.upper()}...",
            total=None,
        )
        await oracle.initialize()
        comparison = await oracle.compare(args.symbol1.upper(), args.symbol2.upper())

    if "error" in comparison:
        console.print(f"[red]Error: {comparison['error']}[/red]")
        return

    console.print()
    console.print(
        Panel(
            f"[bold]{args.symbol1.upper()}[/bold] vs [bold]{args.symbol2.upper()}[/bold]",
            title="⚖️ Asset Comparison",
        )
    )

    table = Table(show_header=True)
    table.add_column("Metric")
    table.add_column(args.symbol1.upper(), justify="center")
    table.add_column(args.symbol2.upper(), justify="center")

    a1, a2 = comparison["asset1"], comparison["asset2"]

    table.add_row("LOS Score", f"{a1['los']:.1f}", f"{a2['los']:.1f}")
    table.add_row("Consensus", f"{a1['consensus']:.0f}%", f"{a2['consensus']:.0f}%")
    table.add_row("Recommendation", a1["recommendation"], a2["recommendation"])

    console.print(table)

    console.print()
    console.print(f"[bold]Verdict:[/bold] {comparison['preferred']}")
    console.print(f"[dim]Reason: {comparison['reason']}[/dim]")


async def cmd_top(args):
    """Handle top command."""
    oracle = LLMAssetOracle()

    category = None if args.category == "all" else args.category

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Finding top-rated assets...", total=None)
        await oracle.initialize()
        top_assets = await oracle.get_top_assets(
            category=category, limit=args.limit
        )

    console.print()
    console.print(
        Panel(
            f"Top {len(top_assets)} {args.category.title()} Assets",
            title="🏆 Rankings",
        )
    )

    table = Table(show_header=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Symbol")
    table.add_column("Name")
    table.add_column("LOS Score", justify="right")
    table.add_column("Consensus", justify="right")
    table.add_column("Rating")

    for i, consensus in enumerate(top_assets, 1):
        asset = consensus.asset
        table.add_row(
            str(i),
            asset.symbol,
            asset.name[:25],
            f"{consensus.los_score:.1f}",
            f"{consensus.consensus_strength:.0f}%",
            consensus.recommendation,
        )

    console.print(table)


async def cmd_status(_args):
    """Handle status command."""
    settings = get_settings()
    oracle = LLMAssetOracle()
    await oracle.initialize()

    console.print()
    console.print(Panel("LLM Asset Oracle", title="🔧 Status"))

    table = Table(show_header=False)
    table.add_column("Setting")
    table.add_column("Value")

    table.add_row("Initialized", "✅ Yes" if oracle.is_initialized else "❌ No")
    table.add_row("Providers", ", ".join(oracle.available_providers) or "None")
    table.add_row("Cache TTL", f"{settings.cache_ttl_seconds}s")
    table.add_row("Model Count", str(settings.consensus_model_count))

    console.print(table)

    # Check API keys
    console.print()
    console.print("[bold]API Key Status:[/bold]")

    key_status = [
        ("OpenAI", bool(settings.openai_api_key)),
        ("Anthropic", bool(settings.anthropic_api_key)),
        ("Google", bool(settings.google_api_key)),
        ("Together", bool(settings.together_api_key)),
        ("Mistral", bool(settings.mistral_api_key)),
    ]

    for name, configured in key_status:
        status = "✅" if configured else "❌"
        console.print(f"  {status} {name}")


def cmd_bot(_args):
    """Handle bot command."""
    from llm_asset_oracle.discord_bot.bot import run_bot

    run_bot()


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
    )

    try:
        if args.command == "analyze":
            asyncio.run(cmd_analyze(args))
        elif args.command == "compare":
            asyncio.run(cmd_compare(args))
        elif args.command == "top":
            asyncio.run(cmd_top(args))
        elif args.command == "status":
            asyncio.run(cmd_status(args))
        elif args.command == "bot":
            cmd_bot(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled[/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
