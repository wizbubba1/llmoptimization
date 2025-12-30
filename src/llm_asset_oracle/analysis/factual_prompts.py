"""
Factual-Only Prompt System

Philosophy:
- Input contains ONLY objective, verifiable facts about the asset
- NO leading questions, opinions, or sentiment-inducing language
- Let the LLM form its own unbiased opinion based purely on facts
- Output format is strictly structured for numerical aggregation

The key insight: By presenting only facts without any subjective framing,
we get the model's genuine assessment rather than an echo of our prompt's bias.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class AssetFacts:
    """
    Factual attributes of an asset.

    All fields should contain ONLY verifiable, objective data.
    No opinions, predictions, or subjective assessments.
    """

    # Identity
    symbol: str
    name: str
    asset_class: str  # "Cryptocurrency", "Stock", "ETF", "Commodity"

    # Age & History
    inception_year: Optional[int] = None
    age_years: Optional[int] = None

    # Market Position
    market_cap_usd: Optional[float] = None
    market_cap_rank: Optional[int] = None
    sector: Optional[str] = None

    # Price Data (factual, current)
    current_price_usd: Optional[float] = None
    price_change_24h_pct: Optional[float] = None
    price_change_7d_pct: Optional[float] = None
    price_change_30d_pct: Optional[float] = None
    all_time_high_usd: Optional[float] = None
    pct_from_ath: Optional[float] = None

    # Volume & Liquidity
    volume_24h_usd: Optional[float] = None
    avg_volume_30d_usd: Optional[float] = None

    # Crypto-specific
    consensus_mechanism: Optional[str] = None  # "Proof of Work", "Proof of Stake"
    total_supply: Optional[float] = None
    circulating_supply: Optional[float] = None
    max_supply: Optional[float] = None

    # Stock-specific
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield_pct: Optional[float] = None
    revenue_usd: Optional[float] = None
    profit_margin_pct: Optional[float] = None

    # Brief factual description (no opinions)
    description: Optional[str] = None


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

FACTUAL_INPUT_TEMPLATE = """Asset Profile:
- Symbol: {symbol}
- Name: {name}
- Type: {asset_class}
{optional_facts}

Based solely on these facts, provide your assessment:

DIRECTION: [BUY or SELL - one word only]
CONFIDENCE: [1-100 - how certain you are]
VIEW: [One sentence - your key reasoning]"""


OUTPUT_INSTRUCTION = """Based solely on these facts, provide your assessment:

DIRECTION: [BUY or SELL - one word only]
CONFIDENCE: [1-100 - how certain you are]
VIEW: [One sentence - your key reasoning]"""


def format_number(value: Optional[float], prefix: str = "$", decimals: int = 2) -> str:
    """Format a number with appropriate scale suffix."""
    if value is None:
        return "N/A"

    if value >= 1_000_000_000_000:
        return f"{prefix}{value/1_000_000_000_000:.{decimals}f}T"
    elif value >= 1_000_000_000:
        return f"{prefix}{value/1_000_000_000:.{decimals}f}B"
    elif value >= 1_000_000:
        return f"{prefix}{value/1_000_000:.{decimals}f}M"
    elif value >= 1_000:
        return f"{prefix}{value/1_000:.{decimals}f}K"
    else:
        return f"{prefix}{value:.{decimals}f}"


def format_pct(value: Optional[float]) -> str:
    """Format percentage with sign."""
    if value is None:
        return "N/A"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def build_factual_prompt(facts: AssetFacts) -> str:
    """
    Build a factual-only prompt from asset facts.

    The prompt contains:
    1. Objective facts about the asset
    2. Simple output instructions (no leading language)

    Args:
        facts: AssetFacts dataclass with verified data

    Returns:
        Complete prompt string
    """
    lines = []

    # Add available facts - only include what we have
    if facts.inception_year:
        lines.append(f"- Founded: {facts.inception_year}")
    if facts.age_years:
        lines.append(f"- Age: {facts.age_years} years")

    if facts.market_cap_usd:
        lines.append(f"- Market Cap: {format_number(facts.market_cap_usd)}")
    if facts.market_cap_rank:
        lines.append(f"- Market Cap Rank: #{facts.market_cap_rank}")

    if facts.sector:
        lines.append(f"- Sector: {facts.sector}")

    if facts.current_price_usd:
        lines.append(f"- Current Price: {format_number(facts.current_price_usd)}")

    # Price changes
    if facts.price_change_24h_pct is not None:
        lines.append(f"- 24h Change: {format_pct(facts.price_change_24h_pct)}")
    if facts.price_change_7d_pct is not None:
        lines.append(f"- 7d Change: {format_pct(facts.price_change_7d_pct)}")
    if facts.price_change_30d_pct is not None:
        lines.append(f"- 30d Change: {format_pct(facts.price_change_30d_pct)}")

    if facts.pct_from_ath is not None:
        lines.append(f"- From ATH: {format_pct(facts.pct_from_ath)}")

    if facts.volume_24h_usd:
        lines.append(f"- 24h Volume: {format_number(facts.volume_24h_usd)}")

    # Crypto-specific
    if facts.consensus_mechanism:
        lines.append(f"- Consensus: {facts.consensus_mechanism}")
    if facts.max_supply:
        lines.append(f"- Max Supply: {facts.max_supply:,.0f}")
    if facts.circulating_supply:
        lines.append(f"- Circulating: {facts.circulating_supply:,.0f}")

    # Stock-specific
    if facts.pe_ratio is not None:
        lines.append(f"- P/E Ratio: {facts.pe_ratio:.2f}")
    if facts.eps is not None:
        lines.append(f"- EPS: ${facts.eps:.2f}")
    if facts.dividend_yield_pct is not None:
        lines.append(f"- Dividend Yield: {facts.dividend_yield_pct:.2f}%")
    if facts.revenue_usd:
        lines.append(f"- Revenue: {format_number(facts.revenue_usd)}")
    if facts.profit_margin_pct is not None:
        lines.append(f"- Profit Margin: {facts.profit_margin_pct:.1f}%")

    # Description (should be factual only)
    if facts.description:
        lines.append(f"- Description: {facts.description}")

    optional_facts = "\n".join(lines) if lines else ""

    return FACTUAL_INPUT_TEMPLATE.format(
        symbol=facts.symbol,
        name=facts.name,
        asset_class=facts.asset_class,
        optional_facts=optional_facts,
    )


# =============================================================================
# PRESET FACTUAL DATA
# =============================================================================

CRYPTO_FACTS = {
    "BTC": AssetFacts(
        symbol="BTC",
        name="Bitcoin",
        asset_class="Cryptocurrency",
        inception_year=2009,
        consensus_mechanism="Proof of Work",
        max_supply=21_000_000,
        description="First decentralized cryptocurrency. Digital store of value. Most widely adopted crypto.",
    ),
    "ETH": AssetFacts(
        symbol="ETH",
        name="Ethereum",
        asset_class="Cryptocurrency",
        inception_year=2015,
        consensus_mechanism="Proof of Stake",
        description="Smart contract platform. Hosts DeFi, NFTs, and dApps. Second largest by market cap.",
    ),
    "SOL": AssetFacts(
        symbol="SOL",
        name="Solana",
        asset_class="Cryptocurrency",
        inception_year=2020,
        consensus_mechanism="Proof of Stake + Proof of History",
        description="High-throughput blockchain. Fast transactions, low fees. Used for DeFi and NFTs.",
    ),
    "XRP": AssetFacts(
        symbol="XRP",
        name="XRP",
        asset_class="Cryptocurrency",
        inception_year=2012,
        max_supply=100_000_000_000,
        description="Digital payment protocol. Focus on cross-border transactions. Used by financial institutions.",
    ),
    "ADA": AssetFacts(
        symbol="ADA",
        name="Cardano",
        asset_class="Cryptocurrency",
        inception_year=2017,
        consensus_mechanism="Proof of Stake (Ouroboros)",
        max_supply=45_000_000_000,
        description="Research-driven blockchain platform. Peer-reviewed academic approach to development.",
    ),
    "DOGE": AssetFacts(
        symbol="DOGE",
        name="Dogecoin",
        asset_class="Cryptocurrency",
        inception_year=2013,
        consensus_mechanism="Proof of Work",
        description="Meme-origin cryptocurrency. Large community. Used for tipping and microtransactions.",
    ),
    "AVAX": AssetFacts(
        symbol="AVAX",
        name="Avalanche",
        asset_class="Cryptocurrency",
        inception_year=2020,
        consensus_mechanism="Proof of Stake (Avalanche Consensus)",
        max_supply=720_000_000,
        description="Layer 1 blockchain. Sub-second finality. Supports custom blockchain networks.",
    ),
    "LINK": AssetFacts(
        symbol="LINK",
        name="Chainlink",
        asset_class="Cryptocurrency",
        inception_year=2017,
        description="Decentralized oracle network. Provides external data to smart contracts. Industry standard.",
    ),
}

STOCK_FACTS = {
    "AAPL": AssetFacts(
        symbol="AAPL",
        name="Apple Inc.",
        asset_class="Stock",
        inception_year=1976,
        sector="Technology",
        description="Consumer electronics, software, services. iPhone, Mac, iPad, Apple Watch, Services.",
    ),
    "MSFT": AssetFacts(
        symbol="MSFT",
        name="Microsoft Corporation",
        asset_class="Stock",
        inception_year=1975,
        sector="Technology",
        description="Software, cloud computing, hardware. Windows, Azure, Office 365, LinkedIn, Gaming.",
    ),
    "GOOGL": AssetFacts(
        symbol="GOOGL",
        name="Alphabet Inc.",
        asset_class="Stock",
        inception_year=1998,
        sector="Technology",
        description="Search, advertising, cloud, hardware. Google Search, YouTube, Google Cloud, Android.",
    ),
    "AMZN": AssetFacts(
        symbol="AMZN",
        name="Amazon.com Inc.",
        asset_class="Stock",
        inception_year=1994,
        sector="Consumer Discretionary",
        description="E-commerce, cloud computing, advertising. AWS, Amazon Retail, Prime, Advertising.",
    ),
    "NVDA": AssetFacts(
        symbol="NVDA",
        name="NVIDIA Corporation",
        asset_class="Stock",
        inception_year=1993,
        sector="Technology",
        description="Semiconductors, GPUs, AI hardware. Data center, gaming, automotive, AI/ML chips.",
    ),
    "TSLA": AssetFacts(
        symbol="TSLA",
        name="Tesla Inc.",
        asset_class="Stock",
        inception_year=2003,
        sector="Consumer Discretionary",
        description="Electric vehicles, energy storage, solar. Model 3/Y/S/X, Powerwall, Supercharger network.",
    ),
    "META": AssetFacts(
        symbol="META",
        name="Meta Platforms Inc.",
        asset_class="Stock",
        inception_year=2004,
        sector="Technology",
        description="Social media, advertising, VR/AR. Facebook, Instagram, WhatsApp, Oculus/Meta Quest.",
    ),
}


def get_preset_facts(symbol: str) -> Optional[AssetFacts]:
    """Get preset facts for a known asset."""
    symbol = symbol.upper()
    return CRYPTO_FACTS.get(symbol) or STOCK_FACTS.get(symbol)


def create_minimal_facts(
    symbol: str, name: str, asset_class: str = "Unknown"
) -> AssetFacts:
    """Create minimal facts for an unknown asset."""
    return AssetFacts(
        symbol=symbol.upper(),
        name=name,
        asset_class=asset_class,
    )
