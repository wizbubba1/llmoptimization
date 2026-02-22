"""
Multi-Mode Discord Bot - LLM Optimization Agent

Modes:
A) Bullish or Bearish - sentiment pie chart
B) Multi-Valuation - up to 8 models, bar chart
C) Solo-Valuation - 1 model, multiple runs, bar chart
D) Technical Analyst - vision models analyze chart screenshot

Flow: /analyze -> mode select -> model/config select -> input modal -> results
"""

import asyncio
import base64
import logging
import os
import sys
from typing import Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

from llm_asset_oracle.engine.query_engine import QueryEngine
from llm_asset_oracle.models.registry import (
    ALL_MODELS, VISION_MODELS, ALL_MODEL_IDS, VISION_MODEL_IDS,
    MAX_MODEL_SELECTION, get_model_name,
)
from llm_asset_oracle.modes.bullish_bearish import run_bullish_bearish
from llm_asset_oracle.modes.multi_valuation import run_multi_valuation
from llm_asset_oracle.modes.solo_valuation import run_solo_valuation
from llm_asset_oracle.modes.technical_analyst import run_technical_analyst
from llm_asset_oracle.charts.generators import (
    generate_sentiment_pie,
    generate_valuation_bars,
    generate_solo_bars,
    generate_long_short_bars,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MODE A: Bullish or Bearish
# =============================================================================

class BullishBearishModal(ui.Modal, title="Bullish or Bearish"):
    """Modal for Mode A input."""

    asset_desc = ui.TextInput(
        label="Describe the Asset",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Ethereum (ETH): Layer 1 smart contract platform with proof of stake...",
        required=True,
        max_length=500,
    )

    time_horizon = ui.TextInput(
        label="Time Horizon",
        placeholder="e.g., 3 months, 6 months, 1 year, 2 years",
        required=True,
        max_length=50,
        default="1 year",
    )

    def __init__(self, engine: QueryEngine):
        super().__init__(timeout=300)
        self.engine = engine

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        embed = discord.Embed(
            title="Bullish or Bearish",
            description=(
                f"**Asset:** {self.asset_desc.value[:100]}\n"
                f"**Time Horizon:** {self.time_horizon.value}\n\n"
                f"Querying {len(ALL_MODEL_IDS)} models..."
            ),
            color=0x3498db,
        )
        status_msg = await interaction.followup.send(embed=embed)

        count = [0]
        lock = asyncio.Lock()

        async def on_result(r):
            async with lock:
                count[0] += 1
                if count[0] % 3 == 0 or count[0] == len(ALL_MODEL_IDS):
                    embed.description = (
                        f"**Asset:** {self.asset_desc.value[:100]}\n"
                        f"**Time Horizon:** {self.time_horizon.value}\n\n"
                        f"Progress: {count[0]}/{len(ALL_MODEL_IDS)} models..."
                    )
                    try:
                        await status_msg.edit(embed=embed)
                    except Exception:
                        pass

        result = await run_bullish_bearish(
            self.engine,
            asset_description=self.asset_desc.value,
            time_horizon=self.time_horizon.value,
            on_result=on_result,
        )

        # Build results embed
        if result.bullish_pct >= result.bearish_pct:
            color = 0x2ecc71  # Green
        else:
            color = 0xe74c3c  # Red

        results_embed = discord.Embed(
            title="Bullish or Bearish - Results",
            description=(
                f"**Asset:** {result.asset_description[:200]}\n"
                f"**Time Horizon:** {result.time_horizon}"
            ),
            color=color,
        )

        results_embed.add_field(
            name="Sentiment Breakdown",
            value=(
                f"**BULLISH:** {result.bullish_count} models ({result.bullish_pct:.0f}%)\n"
                f"**BEARISH:** {result.bearish_count} models ({result.bearish_pct:.0f}%)\n"
                f"**No Response:** {result.unknown_count}"
            ),
            inline=False,
        )

        # Model-by-model list
        bullish_models = [r.model_name for r in result.results if r.sentiment == "BULLISH"]
        bearish_models = [r.model_name for r in result.results if r.sentiment == "BEARISH"]

        if bullish_models:
            results_embed.add_field(
                name=f"BULLISH ({len(bullish_models)})",
                value=", ".join(bullish_models),
                inline=True,
            )
        if bearish_models:
            results_embed.add_field(
                name=f"BEARISH ({len(bearish_models)})",
                value=", ".join(bearish_models),
                inline=True,
            )

        await status_msg.edit(embed=results_embed)

        # Send chart
        chart_buf = generate_sentiment_pie(
            result.bullish_count,
            result.bearish_count,
            result.unknown_count,
            title=f"Bullish vs Bearish: {result.asset_description[:50]}",
        )
        await interaction.followup.send(
            file=discord.File(chart_buf, filename="sentiment.png"),
        )


# =============================================================================
# MODE B: Multi-Valuation
# =============================================================================

class MultiValuationModal(ui.Modal, title="Multi-Valuation"):
    """Modal for Mode B text input (after model selection)."""

    asset_desc = ui.TextInput(
        label="Describe the Asset",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Monad (MON): High-throughput EVM L1 with parallel execution...",
        required=True,
        max_length=500,
    )

    target_time = ui.TextInput(
        label="Target Time",
        placeholder="e.g., Q3 2026, end of 2027",
        required=True,
        max_length=50,
        default="Q4 2026",
    )

    def __init__(self, engine: QueryEngine, selected_model_ids: list[str]):
        super().__init__(timeout=300)
        self.engine = engine
        self.selected_model_ids = selected_model_ids

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        model_names = [get_model_name(mid) for mid in self.selected_model_ids]
        embed = discord.Embed(
            title="Multi-Valuation",
            description=(
                f"**Asset:** {self.asset_desc.value[:100]}\n"
                f"**Target:** {self.target_time.value}\n"
                f"**Models:** {', '.join(model_names)}\n\n"
                f"Querying {len(self.selected_model_ids)} models..."
            ),
            color=0x3498db,
        )
        status_msg = await interaction.followup.send(embed=embed)

        count = [0]
        total = len(self.selected_model_ids)
        lock = asyncio.Lock()

        async def on_result(r):
            async with lock:
                count[0] += 1
                embed.description = (
                    f"**Asset:** {self.asset_desc.value[:100]}\n"
                    f"**Target:** {self.target_time.value}\n\n"
                    f"Progress: {count[0]}/{total} models..."
                )
                try:
                    await status_msg.edit(embed=embed)
                except Exception:
                    pass

        result = await run_multi_valuation(
            self.engine,
            model_ids=self.selected_model_ids,
            asset_description=self.asset_desc.value,
            target_time=self.target_time.value,
            on_result=on_result,
        )

        # Build results embed
        results_embed = discord.Embed(
            title="Multi-Valuation - Results",
            description=(
                f"**Asset:** {result.asset_description[:200]}\n"
                f"**Target:** {result.target_time}"
            ),
            color=0x3498db,
        )

        # Stats
        if result.median_billions >= 1:
            median_fmt = f"${result.median_billions:.1f}B"
            mean_fmt = f"${result.mean_billions:.1f}B"
        else:
            median_fmt = f"${result.median_billions * 1000:.0f}M"
            mean_fmt = f"${result.mean_billions * 1000:.0f}M"

        results_embed.add_field(
            name="Consensus",
            value=(
                f"**Median:** {median_fmt}\n"
                f"**Mean:** {mean_fmt}\n"
                f"**Models:** {result.valid_count}/{result.valid_count + result.failed_count}"
            ),
            inline=False,
        )

        # Model estimates list
        valid_estimates = [e for e in result.estimates if e.success]
        sorted_est = sorted(valid_estimates, key=lambda e: e.value_billions or 0, reverse=True)
        est_lines = [f"**{e.model_name}**: {e.value_formatted}" for e in sorted_est]

        if est_lines:
            results_embed.add_field(
                name="Model Estimates",
                value="\n".join(est_lines)[:1024],
                inline=False,
            )

        await status_msg.edit(embed=results_embed)

        # Send chart
        names = [e.model_name for e in sorted_est]
        values = [e.value_billions for e in sorted_est]

        if values:
            chart_buf = generate_valuation_bars(
                names, values, result.median_billions, result.mean_billions,
                title=f"Market Cap Estimates: {result.asset_description[:40]}",
            )
            await interaction.followup.send(
                file=discord.File(chart_buf, filename="valuation.png"),
            )


class MultiValModelSelect(ui.View):
    """Model selection view for Mode B."""

    def __init__(self, engine: QueryEngine):
        super().__init__(timeout=120)
        self.engine = engine
        self.selected_ids: list[str] = []

        options = [
            discord.SelectOption(label=m.name, value=m.id, description=m.provider)
            for m in ALL_MODELS
        ]

        self.select = ui.Select(
            placeholder="Pick up to 8 models...",
            options=options,
            min_values=1,
            max_values=MAX_MODEL_SELECTION,
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_ids = self.select.values
        modal = MultiValuationModal(self.engine, self.selected_ids)
        await interaction.response.send_modal(modal)
        self.stop()


# =============================================================================
# MODE C: Solo-Valuation
# =============================================================================

class SoloValuationModal(ui.Modal, title="Solo-Valuation"):
    """Modal for Mode C text input."""

    asset_desc = ui.TextInput(
        label="Describe the Asset",
        style=discord.TextStyle.paragraph,
        placeholder="e.g., Solana (SOL): High-performance L1 blockchain...",
        required=True,
        max_length=500,
    )

    target_time = ui.TextInput(
        label="Target Time",
        placeholder="e.g., Q3 2026, end of 2027",
        required=True,
        max_length=50,
        default="Q4 2026",
    )

    def __init__(self, engine: QueryEngine, model_id: str, num_runs: int):
        super().__init__(timeout=300)
        self.engine = engine
        self.model_id = model_id
        self.num_runs = num_runs

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        model_name = get_model_name(self.model_id)
        embed = discord.Embed(
            title="Solo-Valuation",
            description=(
                f"**Asset:** {self.asset_desc.value[:100]}\n"
                f"**Target:** {self.target_time.value}\n"
                f"**Model:** {model_name}\n"
                f"**Runs:** {self.num_runs}\n\n"
                f"Running {self.num_runs} queries..."
            ),
            color=0x9b59b6,
        )
        status_msg = await interaction.followup.send(embed=embed)

        count = [0]
        lock = asyncio.Lock()

        async def on_result(r):
            async with lock:
                count[0] += 1
                embed.description = (
                    f"**Asset:** {self.asset_desc.value[:100]}\n"
                    f"**Model:** {model_name}\n\n"
                    f"Progress: {count[0]}/{self.num_runs} runs..."
                )
                try:
                    await status_msg.edit(embed=embed)
                except Exception:
                    pass

        result = await run_solo_valuation(
            self.engine,
            model_id=self.model_id,
            asset_description=self.asset_desc.value,
            target_time=self.target_time.value,
            num_runs=self.num_runs,
            on_result=on_result,
        )

        # Build results
        if result.median_billions >= 1:
            median_fmt = f"${result.median_billions:.1f}B"
            mean_fmt = f"${result.mean_billions:.1f}B"
        else:
            median_fmt = f"${result.median_billions * 1000:.0f}M"
            mean_fmt = f"${result.mean_billions * 1000:.0f}M"

        results_embed = discord.Embed(
            title=f"Solo-Valuation - {model_name}",
            description=(
                f"**Asset:** {result.asset_description[:200]}\n"
                f"**Target:** {result.target_time}"
            ),
            color=0x9b59b6,
        )

        results_embed.add_field(
            name="Statistics",
            value=(
                f"**Median:** {median_fmt}\n"
                f"**Mean:** {mean_fmt}\n"
                f"**Runs:** {result.valid_count}/{result.num_runs} successful\n"
                f"**Spread:** {result.range_spread:.0f}%"
            ),
            inline=False,
        )

        # Run-by-run list
        run_lines = []
        for est in result.estimates:
            if est.success:
                run_lines.append(f"Run {est.run_number}: {est.value_formatted}")
            else:
                run_lines.append(f"Run {est.run_number}: Failed ({est.error})")

        results_embed.add_field(
            name="Individual Runs",
            value="\n".join(run_lines)[:1024],
            inline=False,
        )

        # Consistency assessment
        if result.range_spread <= 10:
            consistency = "Very Consistent"
        elif result.range_spread <= 25:
            consistency = "Fairly Consistent"
        elif result.range_spread <= 50:
            consistency = "Moderate Variation"
        else:
            consistency = "High Variation"

        results_embed.add_field(
            name="Consistency",
            value=f"**{consistency}** ({result.range_spread:.0f}% spread)",
            inline=False,
        )

        await status_msg.edit(embed=results_embed)

        # Chart
        valid_est = [e for e in result.estimates if e.success]
        if valid_est:
            run_labels = [f"Run {e.run_number}" for e in valid_est]
            values = [e.value_billions for e in valid_est]
            chart_buf = generate_solo_bars(
                run_labels, values, result.median_billions, result.mean_billions,
                model_name=model_name,
            )
            await interaction.followup.send(
                file=discord.File(chart_buf, filename="solo_valuation.png"),
            )


class SoloSetupView(ui.View):
    """Setup view for Mode C: model select + runs select."""

    def __init__(self, engine: QueryEngine):
        super().__init__(timeout=120)
        self.engine = engine
        self.selected_model: str | None = None
        self.selected_runs: int = 3

        # Model select
        model_options = [
            discord.SelectOption(label=m.name, value=m.id, description=m.provider)
            for m in ALL_MODELS
        ]
        self.model_select = ui.Select(
            placeholder="Pick one model...",
            options=model_options,
            min_values=1,
            max_values=1,
            row=0,
        )
        self.model_select.callback = self.model_callback
        self.add_item(self.model_select)

        # Runs select
        runs_options = [
            discord.SelectOption(label=f"{i} runs", value=str(i), default=(i == 3))
            for i in range(1, 6)
        ]
        self.runs_select = ui.Select(
            placeholder="Number of runs...",
            options=runs_options,
            min_values=1,
            max_values=1,
            row=1,
        )
        self.runs_select.callback = self.runs_callback
        self.add_item(self.runs_select)

    async def model_callback(self, interaction: discord.Interaction):
        self.selected_model = self.model_select.values[0]

        if self.selected_model:
            modal = SoloValuationModal(self.engine, self.selected_model, self.selected_runs)
            await interaction.response.send_modal(modal)
            self.stop()
        else:
            await interaction.response.defer()

    async def runs_callback(self, interaction: discord.Interaction):
        self.selected_runs = int(self.runs_select.values[0])
        await interaction.response.defer()


# =============================================================================
# MODE D: Technical Analyst
# =============================================================================

class TechnicalAnalystView(ui.View):
    """Setup view for Mode D: vision model selection."""

    def __init__(self, engine: QueryEngine):
        super().__init__(timeout=120)
        self.engine = engine
        self.selected_ids: list[str] = []

        options = [
            discord.SelectOption(label=m.name, value=m.id, description=m.provider)
            for m in VISION_MODELS
        ]

        self.select = ui.Select(
            placeholder="Pick up to 8 vision models...",
            options=options,
            min_values=1,
            max_values=MAX_MODEL_SELECTION,
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        self.selected_ids = self.select.values
        modal = TechnicalInputModal(self.engine, self.selected_ids)
        await interaction.response.send_modal(modal)
        self.stop()


class TechnicalInputModal(ui.Modal, title="Technical Analyst"):
    """Modal for Mode D: timeframe input."""

    timeframe = ui.TextInput(
        label="Chart Timeframe",
        placeholder="e.g., 4H, 1D, 1W, 1M",
        required=True,
        max_length=20,
        default="1D",
    )

    def __init__(self, engine: QueryEngine, model_ids: list[str]):
        super().__init__(timeout=300)
        self.engine = engine
        self.model_ids = model_ids

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=False)

        model_names = [get_model_name(mid) for mid in self.model_ids]

        embed = discord.Embed(
            title="Technical Analyst",
            description=(
                f"**Timeframe:** {self.timeframe.value}\n"
                f"**Models:** {', '.join(model_names)}\n\n"
                f"Please upload your candlestick chart image now.\n"
                f"Send it as a message in this channel within 60 seconds."
            ),
            color=0xf39c12,
        )
        status_msg = await interaction.followup.send(embed=embed)

        # Wait for image upload
        def check(msg):
            return (
                msg.author == interaction.user
                and msg.channel == interaction.channel
                and len(msg.attachments) > 0
            )

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            embed.description = "Timed out waiting for chart image."
            embed.color = 0xe74c3c
            await status_msg.edit(embed=embed)
            return

        # Download and encode image
        attachment = msg.attachments[0]
        if not any(attachment.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            await interaction.followup.send("Please upload a PNG, JPG, or WebP image.")
            return

        image_bytes = await attachment.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Determine media type
        if attachment.filename.lower().endswith(".png"):
            media_type = "image/png"
        elif attachment.filename.lower().endswith(".webp"):
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

        # Update status
        embed.description = (
            f"**Timeframe:** {self.timeframe.value}\n"
            f"**Models:** {', '.join(model_names)}\n\n"
            f"Analyzing chart with {len(self.model_ids)} models..."
        )
        await status_msg.edit(embed=embed)

        count = [0]
        total = len(self.model_ids)
        lock = asyncio.Lock()

        async def on_result(r):
            async with lock:
                count[0] += 1
                embed.description = (
                    f"**Timeframe:** {self.timeframe.value}\n\n"
                    f"Progress: {count[0]}/{total} models..."
                )
                try:
                    await status_msg.edit(embed=embed)
                except Exception:
                    pass

        result = await run_technical_analyst(
            self.engine,
            model_ids=self.model_ids,
            image_base64=image_b64,
            timeframe=self.timeframe.value,
            image_media_type=media_type,
            on_result=on_result,
        )

        # Results
        if result.long_pct >= result.short_pct:
            color = 0x2ecc71
        else:
            color = 0xe74c3c

        results_embed = discord.Embed(
            title=f"Technical Analyst - {self.timeframe.value} Chart",
            color=color,
        )

        results_embed.add_field(
            name="Consensus",
            value=(
                f"**LONG:** {result.long_count} models ({result.long_pct:.0f}%)\n"
                f"**SHORT:** {result.short_count} models ({result.short_pct:.0f}%)\n"
                f"**No Response:** {result.unknown_count}"
            ),
            inline=False,
        )

        long_models = [r.model_name for r in result.results if r.position == "LONG"]
        short_models = [r.model_name for r in result.results if r.position == "SHORT"]

        if long_models:
            results_embed.add_field(
                name=f"LONG ({len(long_models)})",
                value=", ".join(long_models),
                inline=True,
            )
        if short_models:
            results_embed.add_field(
                name=f"SHORT ({len(short_models)})",
                value=", ".join(short_models),
                inline=True,
            )

        await status_msg.edit(embed=results_embed)

        # Chart
        model_results = [(r.model_name, r.position) for r in result.results if r.position != "UNKNOWN"]
        chart_buf = generate_long_short_bars(
            result.long_count,
            result.short_count,
            model_results,
            title=f"Technical Analysis: {self.timeframe.value}",
        )
        await interaction.followup.send(
            file=discord.File(chart_buf, filename="technical.png"),
        )


# =============================================================================
# MAIN MODE SELECTOR
# =============================================================================

class ModeSelectView(ui.View):
    """Initial mode selection with 4 buttons."""

    def __init__(self, engine: QueryEngine):
        super().__init__(timeout=60)
        self.engine = engine

    @ui.button(label="A) Bullish or Bearish", style=discord.ButtonStyle.green, row=0)
    async def mode_a(self, interaction: discord.Interaction, button: ui.Button):
        modal = BullishBearishModal(self.engine)
        await interaction.response.send_modal(modal)
        self.stop()

    @ui.button(label="B) Multi-Valuation", style=discord.ButtonStyle.blurple, row=0)
    async def mode_b(self, interaction: discord.Interaction, button: ui.Button):
        view = MultiValModelSelect(self.engine)
        await interaction.response.send_message(
            "**Multi-Valuation** - Select up to 8 models:",
            view=view,
            ephemeral=True,
        )
        self.stop()

    @ui.button(label="C) Solo-Valuation", style=discord.ButtonStyle.gray, row=1)
    async def mode_c(self, interaction: discord.Interaction, button: ui.Button):
        view = SoloSetupView(self.engine)
        await interaction.response.send_message(
            "**Solo-Valuation** - Pick a model, then select number of runs.\n"
            "After selecting the model, a form will pop up for asset details.",
            view=view,
            ephemeral=True,
        )
        self.stop()

    @ui.button(label="D) Technical Analyst", style=discord.ButtonStyle.red, row=1)
    async def mode_d(self, interaction: discord.Interaction, button: ui.Button):
        view = TechnicalAnalystView(self.engine)
        await interaction.response.send_message(
            "**Technical Analyst** - Select up to 8 vision-capable models:",
            view=view,
            ephemeral=True,
        )
        self.stop()


# =============================================================================
# BOT
# =============================================================================

class MultiModeBot(commands.Bot):
    """LLM Optimization Agent Discord Bot."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="LLM Optimization Agent",
        )
        self.engine: Optional[QueryEngine] = None

    async def setup_hook(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY not set!")
            return

        self.engine = QueryEngine(api_key)
        logger.info("Query engine initialized")

        await self.add_cog(AgentCommands(self))

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
                name="18 AI models | /analyze",
            )
        )


class AgentCommands(commands.Cog, name="Agent"):
    """Slash commands for the LLM Optimization Agent."""

    def __init__(self, bot: MultiModeBot):
        self.bot = bot

    @app_commands.command(
        name="analyze",
        description="Launch the LLM Optimization Agent - pick a mode"
    )
    async def analyze(self, interaction: discord.Interaction):
        if not self.bot.engine:
            await interaction.response.send_message(
                "Bot not configured. Missing OPENROUTER_API_KEY.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="LLM Optimization Agent",
            description=(
                "**Pick a mode:**\n\n"
                "**A) Bullish or Bearish** - All 18 models vote on sentiment. Pie chart.\n"
                "**B) Multi-Valuation** - Pick up to 8 models for market cap estimates. Bar chart.\n"
                "**C) Solo-Valuation** - Run 1 model up to 5 times to test consistency. Bar chart.\n"
                "**D) Technical Analyst** - Vision models analyze your chart screenshot. Long/Short."
            ),
            color=0x9b59b6,
        )

        view = ModeSelectView(self.bot.engine)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(
        name="models",
        description="List all available AI models"
    )
    async def models(self, interaction: discord.Interaction):
        lines = []
        by_provider: dict[str, list] = {}
        for m in ALL_MODELS:
            by_provider.setdefault(m.provider, []).append(m)

        for provider, models in by_provider.items():
            lines.append(f"**{provider}**")
            for m in models:
                vision_tag = " (vision)" if m.supports_vision else ""
                lines.append(f"  {m.name}{vision_tag}")
            lines.append("")

        embed = discord.Embed(
            title=f"Available Models ({len(ALL_MODELS)})",
            description="\n".join(lines),
            color=0x3498db,
        )
        await interaction.response.send_message(embed=embed)


def run_bot():
    """Run the multi-mode bot."""
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

    bot = MultiModeBot()
    bot.run(token)


if __name__ == "__main__":
    run_bot()
