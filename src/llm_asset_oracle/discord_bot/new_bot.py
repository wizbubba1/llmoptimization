"""
Discord Bot V2 - Multi-Model Consensus Bot

Uses the new OpenRouter-based multi-model oracle for consensus analysis.
"""

import asyncio
import logging
import os
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from llm_asset_oracle.core.multi_model_oracle import (
    MultiModelOracle,
    OracleConfig,
)
from llm_asset_oracle.analysis.consensus_math import (
    ConsensusResult,
    Direction,
    SignalGrade,
    generate_heatmap_data,
    format_heatmap_text,
)

logger = logging.getLogger(__name__)


class OracleBotV2(commands.Bot):
    """Discord bot for Multi-Model LLM Asset Oracle."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            description="Multi-Model LLM Asset Oracle - AI Consensus Analysis",
        )

        self.oracle: Optional[MultiModelOracle] = None

    async def setup_hook(self):
        """Initialize bot components."""
        logger.info("Setting up Oracle Bot V2...")

        # Get config from environment
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY not set!")
            return

        model_count = int(os.getenv("ORACLE_MODEL_COUNT", "15"))
        budget_mode = os.getenv("ORACLE_BUDGET_MODE", "").lower() == "true"

        config = OracleConfig(
            openrouter_api_key=api_key,
            model_count=model_count,
            budget_mode=budget_mode,
        )

        self.oracle = MultiModelOracle(config)

        logger.info(f"Oracle initialized with {self.oracle.model_count} models")

        # Add cogs
        await self.add_cog(ConsensusCommands(self))
        await self.add_cog(RankingCommands(self))
        await self.add_cog(InfoCommands(self))

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
                name=f"{self.oracle.model_count} AI models | /analyze",
            )
        )


def get_grade_color(grade: SignalGrade) -> int:
    """Get Discord embed color for grade."""
    colors = {
        SignalGrade.A_PLUS: 0x00FF00,  # Bright green
        SignalGrade.A: 0x32CD32,  # Lime green
        SignalGrade.B: 0x90EE90,  # Light green
        SignalGrade.C: 0xFFFF00,  # Yellow
        SignalGrade.D: 0xFFA500,  # Orange
        SignalGrade.F: 0xFF0000,  # Red
    }
    return colors.get(grade, 0x808080)


def get_direction_emoji(direction: Direction) -> str:
    """Get emoji for direction."""
    emojis = {
        Direction.STRONG_BUY: "🚀",
        Direction.BUY: "📈",
        Direction.NEUTRAL: "➡️",
        Direction.SELL: "📉",
        Direction.STRONG_SELL: "⚠️",
    }
    return emojis.get(direction, "📊")


class ConsensusCommands(commands.Cog, name="Analysis"):
    """Main analysis commands."""

    def __init__(self, bot: OracleBotV2):
        self.bot = bot

    @app_commands.command(name="analyze", description="Get multi-model AI consensus on an asset")
    @app_commands.describe(
        symbol="Asset symbol (e.g., BTC, AAPL, ETH)",
        show_heatmap="Show model-by-model heatmap",
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        symbol: str,
        show_heatmap: bool = False,
    ):
        """Analyze an asset with multi-model consensus."""
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.oracle.analyze(symbol.upper())

            # Main embed
            embed = self._build_result_embed(result)
            await interaction.followup.send(embed=embed)

            # Heatmap if requested
            if show_heatmap:
                heatmap = format_heatmap_text(generate_heatmap_data(result))
                await interaction.followup.send(heatmap)

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            await interaction.followup.send(
                f"❌ Analysis failed: {str(e)}", ephemeral=True
            )

    @app_commands.command(name="heatmap", description="Show detailed model heatmap for an asset")
    @app_commands.describe(symbol="Asset symbol")
    async def heatmap(self, interaction: discord.Interaction, symbol: str):
        """Show heatmap visualization."""
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.oracle.analyze(symbol.upper())
            heatmap = format_heatmap_text(generate_heatmap_data(result))

            # Brief summary + heatmap
            emoji = get_direction_emoji(result.direction)
            summary = (
                f"{emoji} **{result.symbol}** - {result.direction.value.replace('_', ' ')}\n"
                f"Grade: **{result.grade.value}** | "
                f"Consensus: {result.consensus_strength:.0f}%\n\n"
            )

            await interaction.followup.send(summary + heatmap)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="compare", description="Compare two assets")
    @app_commands.describe(
        symbol1="First asset",
        symbol2="Second asset",
    )
    async def compare(
        self,
        interaction: discord.Interaction,
        symbol1: str,
        symbol2: str,
    ):
        """Compare two assets."""
        await interaction.response.defer(thinking=True)

        try:
            comparison = await self.bot.oracle.compare(
                symbol1.upper(), symbol2.upper()
            )

            if "error" in comparison:
                await interaction.followup.send(f"❌ {comparison['error']}")
                return

            a1, a2 = comparison["asset1"], comparison["asset2"]

            embed = discord.Embed(
                title=f"⚖️ {symbol1.upper()} vs {symbol2.upper()}",
                description=f"Multi-model consensus comparison",
                color=0x3498DB,
            )

            # Asset 1
            embed.add_field(
                name=f"📊 {a1['symbol']}",
                value=(
                    f"**{a1['direction'].replace('_', ' ')}**\n"
                    f"Grade: {a1['grade']}\n"
                    f"Score: {a1['score']:.0f}\n"
                    f"🟢 {a1['buy_pct']:.0f}% | 🔴 {a1['sell_pct']:.0f}%"
                ),
                inline=True,
            )

            # Asset 2
            embed.add_field(
                name=f"📊 {a2['symbol']}",
                value=(
                    f"**{a2['direction'].replace('_', ' ')}**\n"
                    f"Grade: {a2['grade']}\n"
                    f"Score: {a2['score']:.0f}\n"
                    f"🟢 {a2['buy_pct']:.0f}% | 🔴 {a2['sell_pct']:.0f}%"
                ),
                inline=True,
            )

            # Winner
            if comparison["winner"] == "TIE":
                winner_text = "🤝 Too close to call"
            else:
                winner_text = f"🏆 **{comparison['winner']}** (+{comparison['score_diff']:.0f} pts)"

            embed.add_field(
                name="Verdict",
                value=winner_text,
                inline=False,
            )

            embed.set_footer(text=f"Based on {self.bot.oracle.model_count} AI models | Not financial advice")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="quick", description="Quick sentiment check")
    @app_commands.describe(symbol="Asset symbol")
    async def quick(self, interaction: discord.Interaction, symbol: str):
        """Quick analysis with brief output."""
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.oracle.analyze(symbol.upper())

            emoji = get_direction_emoji(result.direction)
            direction = result.direction.value.replace("_", " ")

            msg = (
                f"{emoji} **{result.symbol}**: {direction}\n"
                f"Grade: **{result.grade.value}** | "
                f"Score: {result.grade_score:.0f}/100 | "
                f"Consensus: {result.consensus_strength:.0f}%\n"
                f"Votes: 🟢 {result.buy_pct:.0f}% | 🔴 {result.sell_pct:.0f}%"
            )

            await interaction.followup.send(msg)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    def _build_result_embed(self, result: ConsensusResult) -> discord.Embed:
        """Build rich embed for analysis result."""
        color = get_grade_color(result.grade)
        emoji = get_direction_emoji(result.direction)
        direction = result.direction.value.replace("_", " ")

        embed = discord.Embed(
            title=f"{emoji} {result.symbol} - {direction}",
            description=f"**Grade: {result.grade.value}** ({result.grade_score:.0f}/100)",
            color=color,
        )

        # Vote breakdown
        embed.add_field(
            name="📊 Model Votes",
            value=(
                f"🟢 BUY: {result.buy_votes} ({result.buy_pct:.0f}%)\n"
                f"🔴 SELL: {result.sell_votes} ({result.sell_pct:.0f}%)\n"
                f"⚪ NEUTRAL: {result.neutral_votes} ({result.neutral_pct:.0f}%)"
            ),
            inline=True,
        )

        # Scores
        embed.add_field(
            name="📈 Metrics",
            value=(
                f"Weighted: {result.weighted_score:+.1f}\n"
                f"Consensus: {result.consensus_strength:.0f}%\n"
                f"Avg Conf: {result.avg_confidence:.0f}%"
            ),
            inline=True,
        )

        # Provider breakdown
        if result.provider_breakdown:
            breakdown = []
            for provider, data in list(result.provider_breakdown.items())[:4]:
                total = data["buy"] + data["sell"] + data["neutral"]
                if data["buy"] > data["sell"]:
                    prov_dir = "🟢"
                elif data["sell"] > data["buy"]:
                    prov_dir = "🔴"
                else:
                    prov_dir = "⚪"
                breakdown.append(f"{prov_dir} {provider}: {total} models")

            embed.add_field(
                name="🏢 By Provider",
                value="\n".join(breakdown),
                inline=True,
            )

        # Top views
        if result.common_views:
            views = "\n".join([f"• {v[:80]}" for v in result.common_views[:2]])
            embed.add_field(
                name="💬 Model Views",
                value=views,
                inline=False,
            )

        embed.set_footer(
            text=f"{result.successful_queries} models | ${result.total_cost_usd:.4f} | Not financial advice"
        )

        return embed


class RankingCommands(commands.Cog, name="Rankings"):
    """Asset ranking commands."""

    def __init__(self, bot: OracleBotV2):
        self.bot = bot

    @app_commands.command(name="rank", description="Rank multiple assets by AI consensus")
    @app_commands.describe(
        assets="Comma-separated asset symbols (e.g., BTC,ETH,SOL)",
    )
    async def rank(self, interaction: discord.Interaction, assets: str):
        """Rank multiple assets."""
        await interaction.response.defer(thinking=True)

        try:
            symbols = [s.strip().upper() for s in assets.split(",") if s.strip()]

            if len(symbols) < 2:
                await interaction.followup.send("Please provide at least 2 assets", ephemeral=True)
                return

            if len(symbols) > 10:
                await interaction.followup.send("Maximum 10 assets per ranking", ephemeral=True)
                return

            results = await self.bot.oracle.rank_assets(symbols)

            embed = discord.Embed(
                title="🏆 Asset Ranking",
                description=f"Ranked by multi-model AI consensus",
                color=0xFFD700,
            )

            for i, result in enumerate(results, 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                emoji = get_direction_emoji(result.direction)

                embed.add_field(
                    name=f"{medal} {result.symbol}",
                    value=(
                        f"{emoji} {result.direction.value.replace('_', ' ')}\n"
                        f"Grade: {result.grade.value} | {result.grade_score:.0f}pts\n"
                        f"🟢 {result.buy_pct:.0f}% | 🔴 {result.sell_pct:.0f}%"
                    ),
                    inline=True,
                )

            embed.set_footer(text=f"Based on {self.bot.oracle.model_count} AI models | Not financial advice")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="top_crypto", description="Top cryptocurrency picks")
    async def top_crypto(self, interaction: discord.Interaction):
        """Get top crypto picks."""
        await interaction.response.defer(thinking=True)

        try:
            symbols = ["BTC", "ETH", "SOL", "XRP", "ADA", "AVAX", "LINK", "DOT"]
            results = await self.bot.oracle.rank_assets(symbols)

            embed = discord.Embed(
                title="🏆 Top Crypto by AI Consensus",
                color=0xFFD700,
            )

            for i, result in enumerate(results[:5], 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
                emoji = get_direction_emoji(result.direction)

                embed.add_field(
                    name=f"{medal} {result.symbol}",
                    value=f"{emoji} {result.grade.value} ({result.grade_score:.0f})",
                    inline=True,
                )

            embed.set_footer(text="Not financial advice")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


class InfoCommands(commands.Cog, name="Info"):
    """Informational commands."""

    def __init__(self, bot: OracleBotV2):
        self.bot = bot

    @app_commands.command(name="models", description="List active AI models")
    async def models(self, interaction: discord.Interaction):
        """Show active models."""
        from llm_asset_oracle.llm.openrouter import MODELS_BY_ID

        models = []
        for model_id in self.bot.oracle.models:
            config = MODELS_BY_ID.get(model_id)
            if config:
                models.append(f"• **{config.name}** ({config.provider})")

        embed = discord.Embed(
            title=f"🤖 Active Models ({len(models)})",
            description="\n".join(models[:20]),
            color=0x3498DB,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="methodology", description="How the oracle works")
    async def methodology(self, interaction: discord.Interaction):
        """Explain methodology."""
        embed = discord.Embed(
            title="📚 Multi-Model Consensus Methodology",
            color=0x3498DB,
        )

        embed.add_field(
            name="1️⃣ Factual Input",
            value=(
                "We send ONLY objective facts about each asset to every model - "
                "no leading questions or biased language."
            ),
            inline=False,
        )

        embed.add_field(
            name="2️⃣ Model Voting",
            value=(
                "Each model independently votes:\n"
                "• **Direction**: BUY or SELL\n"
                "• **Confidence**: 1-100%\n"
                "• **View**: One sentence reasoning"
            ),
            inline=False,
        )

        embed.add_field(
            name="3️⃣ Consensus Math",
            value=(
                "We aggregate votes using:\n"
                "• Weighted Score = Σ(direction × confidence)\n"
                "• Consensus Strength = agreement %\n"
                "• Final Grade = combined metric"
            ),
            inline=False,
        )

        embed.add_field(
            name="📊 Grading Scale",
            value=(
                "**A+**: Very strong consensus + direction\n"
                "**A**: Strong signal\n"
                "**B**: Moderate signal\n"
                "**C**: Weak/mixed signal\n"
                "**D/F**: No clear consensus"
            ),
            inline=False,
        )

        embed.set_footer(text="⚠️ This is not financial advice. Do your own research.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Get help")
    async def help_cmd(self, interaction: discord.Interaction):
        """Show help."""
        embed = discord.Embed(
            title="🔮 LLM Asset Oracle - Commands",
            color=0x9B59B6,
        )

        embed.add_field(
            name="📊 Analysis",
            value=(
                "**/analyze <symbol>** - Full multi-model analysis\n"
                "**/quick <symbol>** - Quick sentiment check\n"
                "**/heatmap <symbol>** - Visual model breakdown\n"
                "**/compare <a> <b>** - Compare two assets"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏆 Rankings",
            value=(
                "**/rank <assets>** - Rank comma-separated assets\n"
                "**/top_crypto** - Top cryptocurrency picks"
            ),
            inline=False,
        )

        embed.add_field(
            name="ℹ️ Info",
            value=(
                "**/models** - List active AI models\n"
                "**/methodology** - How it works\n"
                "**/help** - This message"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


def run_bot():
    """Run the Discord bot."""
    import sys
    from dotenv import load_dotenv

    # Load .env file
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

    bot = OracleBotV2()
    bot.run(token)


if __name__ == "__main__":
    run_bot()
