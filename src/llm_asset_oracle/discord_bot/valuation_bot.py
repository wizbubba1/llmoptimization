"""
Valuation Discord Bot

Features:
- /valuate command with modal for fill-in-the-blanks
- Real-time streaming of model results
- Shows the crafted prompt being sent to LLMs
- Chart generation and upload
- Statistical analysis display (factual, no opinions)
"""

import asyncio
import logging
import os
from typing import Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

from llm_asset_oracle.valuation.engine import ValuationEngine, ValuationResult
from llm_asset_oracle.valuation.parser import MarketCapResult
from llm_asset_oracle.valuation.statistics import format_stats_table, ValuationStatistics
from llm_asset_oracle.valuation.models import format_model_list, VALUATION_MODELS
from llm_asset_oracle.valuation.prompt_template import build_simple_prompt
from llm_asset_oracle.valuation.advanced_analysis import run_advanced_analysis, format_advanced_analysis

logger = logging.getLogger(__name__)


# =============================================================================
# MODAL: Fill-in-the-Blanks Form
# =============================================================================

class ValuationModal(ui.Modal, title="🔮 Token Valuation Analysis"):
    """Modal form for entering token details."""

    token_name = ui.TextInput(
        label="Token Name",
        placeholder="e.g., Post Fiat, Monad, Hyperliquid",
        required=True,
        max_length=50,
    )

    ticker = ui.TextInput(
        label="Ticker Symbol",
        placeholder="e.g., PF, MON, HYPE",
        required=True,
        max_length=10,
    )

    year = ui.TextInput(
        label="Target Year",
        placeholder="e.g., 2026",
        required=True,
        max_length=4,
        default="2026",
    )

    description = ui.TextInput(
        label="Description + Key Differentiator",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., high-throughput EVM L1 with parallel execution. Major funding, mainnet 2025.",
        required=True,
        max_length=300,
    )

    factors = ui.TextInput(
        label="Factors to Consider",
        placeholder="e.g., performance, adoption risks, L1 competition, regulatory clarity",
        required=True,
        max_length=200,
    )

    def __init__(self, engine: ValuationEngine):
        super().__init__(timeout=300)  # 5 minute timeout
        self.engine = engine

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission."""
        # Validate year
        try:
            year = int(self.year.value)
            if year < 2024 or year > 2035:
                await interaction.response.send_message(
                    "❌ Year must be between 2024 and 2035",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid year format",
                ephemeral=True
            )
            return

        # Acknowledge immediately
        await interaction.response.defer(thinking=False)

        # Build the prompt that will be sent to all LLMs
        crafted_prompt = build_simple_prompt(
            token_name=self.token_name.value,
            ticker=self.ticker.value.upper(),
            year=year,
            description=self.description.value,
            differentiator="",  # Included in description
            factors=self.factors.value,
        )

        # Create initial status message with prompt preview
        embed = discord.Embed(
            title=f"🔮 Analyzing: {self.token_name.value} ({self.ticker.value.upper()})",
            description=f"**Target Year:** {year}\n\n⏳ Querying {len(VALUATION_MODELS)} AI models...",
            color=0x3498db,
        )

        # Show the crafted prompt
        embed.add_field(
            name="📜 Prompt Being Sent to All LLMs",
            value=f"```\n{crafted_prompt[:900]}{'...' if len(crafted_prompt) > 900 else ''}\n```",
            inline=False,
        )

        embed.set_footer(text="Results will appear below as models respond...")

        status_message = await interaction.followup.send(embed=embed)

        # Track results for live updates
        results_so_far: list[MarketCapResult] = []
        update_lock = asyncio.Lock()

        async def on_model_result(result: MarketCapResult):
            """Called when each model responds."""
            async with update_lock:
                results_so_far.append(result)

                # Update the message with progress
                await update_progress_message(
                    status_message,
                    self.token_name.value,
                    self.ticker.value.upper(),
                    year,
                    results_so_far,
                    len(VALUATION_MODELS),
                    crafted_prompt,
                )

        # Run valuation
        try:
            result = await self.engine.valuate(
                token_name=self.token_name.value,
                ticker=self.ticker.value.upper(),
                year=year,
                category="",
                description=self.description.value,
                differentiator="",  # Included in description
                factors=self.factors.value,
                on_result=on_model_result,
            )

            # Send final results
            await send_final_results(interaction, status_message, result, crafted_prompt)

        except Exception as e:
            logger.error(f"Valuation failed: {e}")
            await interaction.followup.send(
                f"❌ Valuation failed: {str(e)}",
                ephemeral=True,
            )


async def update_progress_message(
    message: discord.Message,
    token_name: str,
    ticker: str,
    year: int,
    results: list[MarketCapResult],
    total_models: int,
    crafted_prompt: str,
):
    """Update the progress message as results come in."""
    successful = [r for r in results if r.value_billions is not None]
    failed = [r for r in results if r.value_billions is None]

    # Build progress text with full reasoning (no truncation)
    progress_lines = []

    for r in successful[-5:]:  # Show last 5 successful
        line = f"✅ **{r.model_name}**: {r.value_formatted}"
        if r.reasoning:
            # Show full reasoning (Discord embed field limit is 1024, but we have multiple)
            line += f"\n   ↳ *{r.reasoning}*"
        progress_lines.append(line)

    for r in failed[-2:]:  # Show last 2 failed
        progress_lines.append(f"⚠️ {r.model_name}: {r.error or 'Parse failed'}")

    progress_text = "\n".join(progress_lines) if progress_lines else "Waiting for results..."

    # Calculate running stats if we have data
    stats_text = ""
    if len(successful) >= 2:
        values = [r.value_billions for r in successful]
        avg = sum(values) / len(values)
        stats_text = f"\n\n📊 **Running Average:** ${avg:.1f}B ({len(successful)} models)"

    embed = discord.Embed(
        title=f"🔮 Analyzing: {token_name} ({ticker})",
        description=(
            f"**Target Year:** {year}\n\n"
            f"⏳ Progress: {len(results)}/{total_models} models\n\n"
            f"{progress_text}"
            f"{stats_text}"
        ),
        color=0x3498db,
    )

    # Progress bar
    pct = len(results) / total_models
    bar_filled = int(pct * 20)
    bar_empty = 20 - bar_filled
    progress_bar = "█" * bar_filled + "░" * bar_empty
    embed.add_field(
        name="Progress",
        value=f"`[{progress_bar}]` {pct*100:.0f}%",
        inline=False,
    )

    # Keep showing the full prompt
    embed.add_field(
        name="📜 Prompt Sent to LLMs",
        value=f"```\n{crafted_prompt}\n```",
        inline=False,
    )

    try:
        await message.edit(embed=embed)
    except Exception as e:
        logger.warning(f"Failed to update progress: {e}")


async def send_final_results(
    interaction: discord.Interaction,
    status_message: discord.Message,
    result: ValuationResult,
    crafted_prompt: str,
):
    """Send the final results with statistics and chart."""
    stats = result.statistics

    if not stats or stats.successful_parses == 0:
        embed = discord.Embed(
            title=f"❌ Valuation Failed: {result.prompt_data.token_name}",
            description="No models returned parseable market cap estimates.",
            color=0xe74c3c,
        )
        await status_message.edit(embed=embed)
        return

    # Run advanced analysis
    advanced = run_advanced_analysis(stats.estimates)

    # Determine color based on refined confidence
    color_map = {
        "high": 0x2ecc71,      # Green
        "moderate": 0xf39c12,  # Orange
        "low": 0xe67e22,       # Dark orange
        "very_low": 0xe74c3c,  # Red
    }
    color = color_map.get(advanced.confidence_level, 0x95a5a6)

    # Main results embed
    embed = discord.Embed(
        title=f"🔮 Valuation Complete: {stats.token_name} ({stats.ticker})",
        description=f"**Target Year:** {stats.target_year}",
        color=color,
    )

    # ========== ORIGINAL STATS SECTION ==========
    embed.add_field(
        name="💰 Consensus Valuation",
        value=(
            f"**Median:** {stats.median_formatted}\n"
            f"**Mean:** {stats.mean_formatted}\n"
            f"**Range:** {stats.range_formatted}"
        ),
        inline=True,
    )

    embed.add_field(
        name="📊 Statistics",
        value=(
            f"**Agreement:** {stats.consensus_strength:.0f}%\n"
            f"**IQR:** {stats.iqr_formatted}\n"
            f"**95% CI:** {stats.ci_formatted}"
        ),
        inline=True,
    )

    embed.add_field(
        name="🤖 Models",
        value=(
            f"**Successful:** {stats.successful_parses}/{stats.total_models}\n"
            f"**Outliers:** {stats.outlier_count}"
        ),
        inline=True,
    )

    # ========== MODEL ESTIMATES WITH REASONING ==========
    sorted_estimates = sorted(
        [e for e in stats.estimates if e.value_billions],
        key=lambda x: x.value_billions,
        reverse=True
    )

    # Build model lines with full reasoning
    model_sections = []
    for est in sorted_estimates:
        emoji = "🟢" if abs(est.value_billions - stats.median_value) / stats.median_value <= 0.2 else "🟡"
        line = f"{emoji} **{est.model_name}**: {est.value_formatted}"
        if est.reasoning:
            line += f"\n↳ *{est.reasoning}*"
        model_sections.append(line)

    # Split into multiple embed fields to avoid Discord limits
    if model_sections:
        first_half = model_sections[:len(model_sections)//2 + 1]
        second_half = model_sections[len(model_sections)//2 + 1:]

        embed.add_field(
            name="📋 Model Estimates",
            value="\n".join(first_half)[:1024],
            inline=False,
        )

        if second_half:
            embed.add_field(
                name="📋 More Estimates",
                value="\n".join(second_half)[:1024],
                inline=False,
            )

    # Distribution Analysis
    embed.add_field(
        name="📈 Distribution Analysis",
        value=stats.verdict[:500],
        inline=False,
    )

    # ========== DATA SCIENCE SECTION (CONDENSED) ==========
    confidence_emoji = {"high": "🟢", "moderate": "🟡", "low": "🟠", "very_low": "🔴"}
    emoji = confidence_emoji.get(advanced.confidence_level, "⚪")
    rs = advanced.refined_stats

    # Outlier names
    outlier_text = ", ".join(advanced.outliers.outlier_models[:3]) if advanced.outliers.outlier_models else "None"

    embed.add_field(
        name=f"{emoji} Data Science Analysis",
        value=(
            f"**Best Estimate:** ${advanced.best_estimate:.1f}B | "
            f"**Range:** ${advanced.estimate_range[0]:.1f}B - ${advanced.estimate_range[1]:.1f}B\n"
            f"**Confidence:** {advanced.confidence_level.upper()} | "
            f"**Consensus:** {rs.raw_consensus:.0f}% → {rs.refined_consensus:.0f}% (cleaned)\n"
            f"**Trimmed Mean:** ${rs.trimmed_mean:.1f}B | **MAD:** ${rs.mad:.1f}B\n"
            f"**Outliers Removed:** {outlier_text}\n"
            f"**Cluster:** {advanced.clusters.division_description}"
        ),
        inline=False,
    )

    # Show the full prompt
    embed.add_field(
        name="📜 Prompt Used",
        value=f"```\n{crafted_prompt}\n```",
        inline=False,
    )

    embed.set_footer(
        text=f"Completed in {result.total_time_ms/1000:.1f}s | Advanced analysis with outlier removal & clustering"
    )

    # Edit the status message with final results
    await status_message.edit(embed=embed)

    # Generate and send chart
    try:
        from llm_asset_oracle.valuation.charts import generate_valuation_chart
        chart_buf = generate_valuation_chart(stats)

        chart_file = discord.File(chart_buf, filename="valuation_chart.png")
        await interaction.followup.send(
            content=f"📊 **Valuation Chart for {stats.token_name}**",
            file=chart_file,
        )
    except Exception as e:
        logger.error(f"Failed to generate chart: {e}")


# =============================================================================
# BOT SETUP
# =============================================================================

class ValuationBot(commands.Bot):
    """Discord bot for LLM valuation analysis."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="LLM Asset Oracle - Multi-Model Valuation Analysis",
        )

        self.engine: Optional[ValuationEngine] = None

    async def setup_hook(self):
        """Initialize bot."""
        logger.info("Setting up Valuation Bot...")

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY not set!")
            return

        self.engine = ValuationEngine(api_key)
        logger.info(f"Engine initialized with {len(VALUATION_MODELS)} models")

        # Add command cog
        await self.add_cog(ValuationCommands(self))

        # Sync commands
        guild_ids = os.getenv("DISCORD_GUILD_IDS", "")
        if guild_ids:
            for gid in guild_ids.split(","):
                if gid.strip():
                    guild = discord.Object(id=int(gid.strip()))
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                    logger.info(f"Synced to guild {gid}")
        else:
            await self.tree.sync()
            logger.info("Synced global commands")

    async def on_ready(self):
        logger.info(f"Bot ready: {self.user}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(VALUATION_MODELS)} AI models | /valuate",
            )
        )


class ValuationCommands(commands.Cog, name="Valuation"):
    """Valuation commands."""

    def __init__(self, bot: ValuationBot):
        self.bot = bot

    @app_commands.command(
        name="valuate",
        description="Get AI consensus market cap valuation for a token"
    )
    async def valuate(self, interaction: discord.Interaction):
        """Open the valuation form."""
        if not self.bot.engine:
            await interaction.response.send_message(
                "❌ Bot not properly configured. Missing OPENROUTER_API_KEY.",
                ephemeral=True,
            )
            return

        modal = ValuationModal(self.bot.engine)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="models",
        description="List all AI models used for valuation"
    )
    async def models(self, interaction: discord.Interaction):
        """Show model list."""
        embed = discord.Embed(
            title="🤖 Valuation Models",
            description=format_model_list(),
            color=0x3498db,
        )
        embed.set_footer(text="These models are queried for each valuation analysis")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="help",
        description="How to use the valuation bot"
    )
    async def help_cmd(self, interaction: discord.Interaction):
        """Show help."""
        embed = discord.Embed(
            title="🔮 LLM Asset Oracle - Valuation Bot",
            description=(
                "Get AI consensus market cap valuations for crypto tokens.\n\n"
                "**How it works:**\n"
                "1. Use `/valuate` to open the form\n"
                "2. Fill in token details\n"
                "3. Watch as 15 AI models analyze your token\n"
                "4. Get statistical consensus + charts"
            ),
            color=0x9b59b6,
        )

        embed.add_field(
            name="📝 Form Fields",
            value=(
                "**Token Name** - e.g., Post Fiat\n"
                "**Ticker** - e.g., PF\n"
                "**Year** - Target year (2024-2035)\n"
                "**Description** - What it does + unique features\n"
                "**Factors** - What to consider (risks, competition)"
            ),
            inline=False,
        )

        embed.add_field(
            name="📊 Output",
            value=(
                "• The exact prompt sent to all models\n"
                "• Median & Mean valuation\n"
                "• Model-by-model estimates + reasoning\n"
                "• Statistical charts\n"
                "• Confidence intervals"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 Tips",
            value=(
                "• Be specific and factual in descriptions\n"
                "• Avoid hype language - just state facts\n"
                "• Include key differentiators\n"
                "• Mention relevant competitors/comparables"
            ),
            inline=False,
        )

        embed.set_footer(text="⚠️ Not financial advice. Do your own research.")
        await interaction.response.send_message(embed=embed)


def run_bot():
    """Run the valuation bot."""
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        logger.error("DISCORD_BOT_TOKEN not set")
        sys.exit(1)

    bot = ValuationBot()
    bot.run(token)


if __name__ == "__main__":
    run_bot()
