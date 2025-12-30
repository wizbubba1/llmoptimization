"""Discord bot implementation for LLM Asset Oracle."""

import asyncio
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from llm_asset_oracle.core.config import get_settings
from llm_asset_oracle.core.oracle import LLMAssetOracle
from llm_asset_oracle.analysis.insights import InsightExtractor

logger = logging.getLogger(__name__)


class OracleBot(commands.Bot):
    """Discord bot for LLM Asset Oracle."""

    def __init__(self):
        """Initialize the bot."""
        intents = discord.Intents.default()
        intents.message_content = True

        super().__init__(
            command_prefix="!oracle ",
            intents=intents,
            description="LLM Asset Oracle - AI-powered asset analysis",
        )

        self.oracle: Optional[LLMAssetOracle] = None
        self.settings = get_settings()

    async def setup_hook(self):
        """Called when the bot is ready to set up."""
        logger.info("Setting up Oracle bot...")

        # Initialize the Oracle
        self.oracle = LLMAssetOracle(self.settings)
        await self.oracle.initialize()

        # Add cogs
        await self.add_cog(AnalysisCog(self))
        await self.add_cog(RankingCog(self))
        await self.add_cog(InfoCog(self))

        # Sync slash commands
        if self.settings.guild_id_list:
            for guild_id in self.settings.guild_id_list:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Synced commands to guild {guild_id}")
        else:
            await self.tree.sync()
            logger.info("Synced global commands")

    async def on_ready(self):
        """Called when the bot is fully ready."""
        logger.info(f"Bot is ready! Logged in as {self.user}")
        logger.info(f"Connected to {len(self.guilds)} guilds")

        # Set presence
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="the markets | /analyze",
            )
        )


class AnalysisCog(commands.Cog, name="Analysis"):
    """Commands for analyzing assets."""

    def __init__(self, bot: OracleBot):
        self.bot = bot

    @app_commands.command(name="analyze", description="Analyze an asset using multiple AI models")
    @app_commands.describe(
        symbol="The asset symbol (e.g., BTC, AAPL, ETH)",
        detailed="Show detailed breakdown (default: False)",
    )
    async def analyze(
        self,
        interaction: discord.Interaction,
        symbol: str,
        detailed: bool = False,
    ):
        """Analyze an asset and show consensus rating."""
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.oracle.analyze(symbol.upper())
            consensus = result.consensus

            # Create embed
            embed_data = InsightExtractor.generate_discord_embed_data(consensus)
            embed = discord.Embed(
                title=embed_data["title"],
                description=embed_data["description"],
                color=embed_data["color"],
            )

            for field in embed_data["fields"]:
                embed.add_field(
                    name=field["name"],
                    value=field["value"],
                    inline=field.get("inline", True),
                )

            # Add market data if available
            if result.market_data and result.market_data.get("price"):
                price = result.market_data["price"]
                change = result.market_data.get("change_24h", 0)
                change_emoji = "🟢" if change >= 0 else "🔴"
                embed.add_field(
                    name="💰 Current Price",
                    value=f"${price:,.2f} {change_emoji} {change:+.2f}%",
                    inline=True,
                )

            # Add trend if available
            if result.score_trend:
                trend_emoji = {"up": "📈", "down": "📉", "stable": "➡️"}.get(
                    result.score_trend, ""
                )
                embed.add_field(
                    name="📊 Score Trend",
                    value=f"{trend_emoji} {result.score_trend.title()}",
                    inline=True,
                )

            embed.set_footer(text=embed_data["footer"]["text"])
            embed.timestamp = consensus.analysis_timestamp

            await interaction.followup.send(embed=embed)

            # Send detailed breakdown if requested
            if detailed:
                detail_embed = discord.Embed(
                    title=f"📊 Detailed Analysis: {symbol.upper()}",
                    color=embed_data["color"],
                )

                # Model breakdown
                model_details = []
                for response in consensus.responses:
                    score = response.rating.overall_score
                    model_details.append(
                        f"**{response.provider}** ({response.model}): {score:.1f}/10"
                    )
                detail_embed.add_field(
                    name="🤖 Model Scores",
                    value="\n".join(model_details),
                    inline=False,
                )

                # Statistics
                stats = (
                    f"Mean: {consensus.metrics.mean:.2f}\n"
                    f"Std Dev: {consensus.metrics.std_dev:.2f}\n"
                    f"Range: {consensus.metrics.range:.2f}\n"
                    f"95% CI: {consensus.confidence_interval[0]:.1f} - {consensus.confidence_interval[1]:.1f}"
                )
                detail_embed.add_field(
                    name="📈 Statistics",
                    value=stats,
                    inline=True,
                )

                await interaction.followup.send(embed=detail_embed)

        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            await interaction.followup.send(
                f"❌ Failed to analyze **{symbol.upper()}**: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="compare", description="Compare two assets")
    @app_commands.describe(
        symbol1="First asset symbol",
        symbol2="Second asset symbol",
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
                await interaction.followup.send(
                    f"❌ Comparison failed: {comparison['error']}",
                    ephemeral=True,
                )
                return

            # Create comparison embed
            embed = discord.Embed(
                title=f"⚖️ {symbol1.upper()} vs {symbol2.upper()}",
                description=f"AI consensus comparison across multiple models",
                color=0x3498DB,
            )

            # Asset 1
            a1 = comparison["asset1"]
            embed.add_field(
                name=f"📊 {a1['symbol']}",
                value=(
                    f"**LOS Score**: {a1['los']:.1f}/100\n"
                    f"**Consensus**: {a1['consensus']:.0f}%\n"
                    f"**Rating**: {a1['recommendation']}"
                ),
                inline=True,
            )

            # Asset 2
            a2 = comparison["asset2"]
            embed.add_field(
                name=f"📊 {a2['symbol']}",
                value=(
                    f"**LOS Score**: {a2['los']:.1f}/100\n"
                    f"**Consensus**: {a2['consensus']:.0f}%\n"
                    f"**Rating**: {a2['recommendation']}"
                ),
                inline=True,
            )

            # Winner
            if comparison["preferred"] != "Neither (too close to call)":
                winner_emoji = "🏆"
            else:
                winner_emoji = "🤝"

            embed.add_field(
                name=f"{winner_emoji} Verdict",
                value=(
                    f"**Preferred**: {comparison['preferred']}\n"
                    f"**Reason**: {comparison['reason']}"
                ),
                inline=False,
            )

            embed.set_footer(text="Based on multi-LLM consensus analysis | Not financial advice")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            await interaction.followup.send(
                f"❌ Comparison failed: {str(e)}",
                ephemeral=True,
            )

    @app_commands.command(name="quick", description="Quick sentiment check for an asset")
    @app_commands.describe(symbol="The asset symbol")
    async def quick(self, interaction: discord.Interaction, symbol: str):
        """Quick sentiment check."""
        await interaction.response.defer(thinking=True)

        try:
            result = await self.bot.oracle.quick_analyze(symbol.upper())

            if "error" in result:
                await interaction.followup.send(
                    f"❌ Error: {result['error']}", ephemeral=True
                )
                return

            # Simple response
            los = result["los_score"]
            rec = result["recommendation"]

            # Emoji based on recommendation
            emoji_map = {
                "STRONG BUY": "🚀",
                "BUY": "📈",
                "HOLD": "➡️",
                "SELL": "📉",
                "STRONG SELL": "⚠️",
            }
            emoji = emoji_map.get(rec, "📊")

            await interaction.followup.send(
                f"{emoji} **{result['symbol']}** ({result['name']})\n"
                f"LOS Score: **{los:.1f}**/100 | Recommendation: **{rec}**\n"
                f"Consensus: {result['consensus_strength']:.0f}% ({result['models_queried']} models)"
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class RankingCog(commands.Cog, name="Rankings"):
    """Commands for asset rankings."""

    def __init__(self, bot: OracleBot):
        self.bot = bot

    @app_commands.command(name="top", description="Get top-rated assets")
    @app_commands.describe(
        category="Asset category (crypto, stock, or all)",
        limit="Number of results (default: 5, max: 10)",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Cryptocurrency", value="crypto"),
            app_commands.Choice(name="Stocks", value="stock"),
            app_commands.Choice(name="All", value="all"),
        ]
    )
    async def top(
        self,
        interaction: discord.Interaction,
        category: str = "all",
        limit: int = 5,
    ):
        """Get top-rated assets by LOS score."""
        await interaction.response.defer(thinking=True)

        limit = min(max(1, limit), 10)

        try:
            cat = None if category == "all" else category
            top_assets = await self.bot.oracle.get_top_assets(
                category=cat, limit=limit
            )

            if not top_assets:
                await interaction.followup.send(
                    "No assets analyzed yet. Try `/analyze <symbol>` first!",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title=f"🏆 Top {len(top_assets)} {category.title()} Assets",
                description="Ranked by LLM Optimization Score (LOS)",
                color=0xFFD700,
            )

            for i, consensus in enumerate(top_assets, 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
                asset = consensus.asset

                embed.add_field(
                    name=f"{medal} {asset.symbol}",
                    value=(
                        f"**{asset.name}**\n"
                        f"LOS: {consensus.los_score:.1f} | {consensus.recommendation}\n"
                        f"Consensus: {consensus.consensus_strength:.0f}%"
                    ),
                    inline=True,
                )

            embed.set_footer(text="Based on multi-LLM analysis | Not financial advice")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Top assets failed: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="picks", description="Get high-conviction picks")
    @app_commands.describe(category="Asset category (crypto, stock, or all)")
    @app_commands.choices(
        category=[
            app_commands.Choice(name="Cryptocurrency", value="crypto"),
            app_commands.Choice(name="Stocks", value="stock"),
            app_commands.Choice(name="All", value="all"),
        ]
    )
    async def picks(self, interaction: discord.Interaction, category: str = "all"):
        """Get high-conviction picks (high LOS + high consensus)."""
        await interaction.response.defer(thinking=True)

        try:
            cat = None if category == "all" else category
            picks = await self.bot.oracle.get_high_conviction_picks(
                category=cat, limit=5
            )

            if not picks:
                await interaction.followup.send(
                    "No high-conviction picks found. "
                    "This requires assets with both high LOS scores and high model consensus.",
                    ephemeral=True,
                )
                return

            embed = discord.Embed(
                title="💎 High Conviction Picks",
                description="Assets with both high LOS scores AND strong model agreement",
                color=0x9B59B6,
            )

            for consensus in picks:
                asset = consensus.asset
                embed.add_field(
                    name=f"✨ {asset.symbol} - {asset.name}",
                    value=(
                        f"**LOS Score**: {consensus.los_score:.1f}/100\n"
                        f"**Consensus**: {consensus.consensus_strength:.0f}%\n"
                        f"**Rating**: {consensus.recommendation}\n"
                        f"**Votes**: 🟢{consensus.bullish_models} ⚪{consensus.neutral_models} 🔴{consensus.bearish_models}"
                    ),
                    inline=False,
                )

            embed.set_footer(text="High conviction = High score + High agreement | Not financial advice")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"Picks failed: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


class InfoCog(commands.Cog, name="Information"):
    """Informational commands."""

    def __init__(self, bot: OracleBot):
        self.bot = bot

    @app_commands.command(name="methodology", description="Learn how LOS scores are calculated")
    async def methodology(self, interaction: discord.Interaction):
        """Explain the scoring methodology."""
        embed = discord.Embed(
            title="📚 LLM Optimization Score (LOS) Methodology",
            description="How we calculate asset ratings",
            color=0x3498DB,
        )

        embed.add_field(
            name="🔬 Scientific Approach",
            value=(
                "We query multiple AI models with identical, standardized prompts "
                "and aggregate their responses using statistical methods."
            ),
            inline=False,
        )

        embed.add_field(
            name="🤖 Models Used",
            value=(
                "• GPT-4 (OpenAI)\n"
                "• Claude (Anthropic)\n"
                "• Gemini (Google)\n"
                "• Llama (Meta/Together)\n"
                "• Mistral"
            ),
            inline=True,
        )

        embed.add_field(
            name="📊 Scoring Components",
            value=(
                "• Overall Rating (25%)\n"
                "• Short-term Outlook (10%)\n"
                "• Medium-term Outlook (15%)\n"
                "• Long-term Outlook (15%)\n"
                "• Fundamentals (10%)\n"
                "• Momentum (10%)\n"
                "• Sentiment (5%)\n"
                "• Risk Adjustment"
            ),
            inline=True,
        )

        embed.add_field(
            name="🎯 LOS Score (0-100)",
            value=(
                "The LOS Score combines the mean rating with a consensus multiplier. "
                "Higher agreement between models boosts the score, while disagreement reduces it."
            ),
            inline=False,
        )

        embed.add_field(
            name="📈 Consensus Strength",
            value=(
                "Measures how much models agree. Based on coefficient of variation:\n"
                "• 80-100%: Very High Consensus\n"
                "• 60-80%: High Consensus\n"
                "• 40-60%: Moderate Consensus\n"
                "• <40%: Low/No Consensus"
            ),
            inline=False,
        )

        embed.add_field(
            name="⚠️ Disclaimer",
            value=(
                "This tool is for informational and entertainment purposes only. "
                "It is NOT financial advice. Always do your own research and consult "
                "qualified financial advisors before making investment decisions."
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="status", description="Check bot and Oracle status")
    async def status(self, interaction: discord.Interaction):
        """Show bot status."""
        embed = discord.Embed(
            title="🔧 Oracle Status",
            color=0x2ECC71 if self.bot.oracle.is_initialized else 0xE74C3C,
        )

        embed.add_field(
            name="Status",
            value="✅ Online" if self.bot.oracle.is_initialized else "❌ Not Ready",
            inline=True,
        )

        embed.add_field(
            name="Active Providers",
            value=", ".join(self.bot.oracle.available_providers) or "None",
            inline=True,
        )

        embed.add_field(
            name="Guilds",
            value=str(len(self.bot.guilds)),
            inline=True,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Get help using the Oracle")
    async def help_command(self, interaction: discord.Interaction):
        """Show help information."""
        embed = discord.Embed(
            title="🔮 LLM Asset Oracle - Help",
            description="AI-powered multi-model asset analysis",
            color=0x9B59B6,
        )

        embed.add_field(
            name="📊 Analysis Commands",
            value=(
                "**/analyze <symbol>** - Full analysis with consensus\n"
                "**/quick <symbol>** - Quick sentiment check\n"
                "**/compare <a> <b>** - Compare two assets"
            ),
            inline=False,
        )

        embed.add_field(
            name="🏆 Ranking Commands",
            value=(
                "**/top [category]** - Top-rated assets\n"
                "**/picks [category]** - High conviction picks"
            ),
            inline=False,
        )

        embed.add_field(
            name="ℹ️ Info Commands",
            value=(
                "**/methodology** - How LOS is calculated\n"
                "**/status** - Bot status\n"
                "**/help** - This message"
            ),
            inline=False,
        )

        embed.add_field(
            name="💡 Tips",
            value=(
                "• Use standard symbols: BTC, ETH, AAPL, GOOGL\n"
                "• First analysis may take 10-30 seconds\n"
                "• Results are cached for faster repeat queries\n"
                "• Higher consensus = more reliable rating"
            ),
            inline=False,
        )

        await interaction.response.send_message(embed=embed)


def run_bot():
    """Run the Discord bot."""
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    settings = get_settings()

    if not settings.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN not set in environment")
        sys.exit(1)

    bot = OracleBot()
    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    run_bot()
