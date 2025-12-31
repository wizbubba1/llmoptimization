"""Pre-defined asset lists and lookup utilities."""

from llm_asset_oracle.core.models import Asset, AssetType


# =============================================================================
# Popular Cryptocurrencies
# =============================================================================

POPULAR_CRYPTOS = [
    Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type=AssetType.CRYPTO,
        description="The first and largest cryptocurrency by market cap. Digital gold and store of value.",
    ),
    Asset(
        symbol="ETH",
        name="Ethereum",
        asset_type=AssetType.CRYPTO,
        description="Leading smart contract platform. Powers DeFi, NFTs, and decentralized applications.",
    ),
    Asset(
        symbol="SOL",
        name="Solana",
        asset_type=AssetType.CRYPTO,
        description="High-performance blockchain known for speed and low transaction costs.",
    ),
    Asset(
        symbol="XRP",
        name="Ripple",
        asset_type=AssetType.CRYPTO,
        description="Digital payment protocol and cryptocurrency for cross-border transactions.",
    ),
    Asset(
        symbol="ADA",
        name="Cardano",
        asset_type=AssetType.CRYPTO,
        description="Proof-of-stake blockchain platform with focus on academic research.",
    ),
    Asset(
        symbol="DOGE",
        name="Dogecoin",
        asset_type=AssetType.CRYPTO,
        description="Meme cryptocurrency that gained mainstream attention. Community-driven.",
    ),
    Asset(
        symbol="DOT",
        name="Polkadot",
        asset_type=AssetType.CRYPTO,
        description="Multi-chain protocol enabling cross-blockchain transfers.",
    ),
    Asset(
        symbol="AVAX",
        name="Avalanche",
        asset_type=AssetType.CRYPTO,
        description="Layer 1 blockchain platform for dApps and custom blockchain networks.",
    ),
    Asset(
        symbol="LINK",
        name="Chainlink",
        asset_type=AssetType.CRYPTO,
        description="Decentralized oracle network providing real-world data to smart contracts.",
    ),
    Asset(
        symbol="MATIC",
        name="Polygon",
        asset_type=AssetType.CRYPTO,
        description="Ethereum scaling solution for faster and cheaper transactions.",
    ),
    Asset(
        symbol="UNI",
        name="Uniswap",
        asset_type=AssetType.CRYPTO,
        description="Leading decentralized exchange protocol on Ethereum.",
    ),
    Asset(
        symbol="ATOM",
        name="Cosmos",
        asset_type=AssetType.CRYPTO,
        description="Interoperability protocol connecting independent blockchains.",
    ),
    Asset(
        symbol="LTC",
        name="Litecoin",
        asset_type=AssetType.CRYPTO,
        description="Early Bitcoin fork with faster block times. Digital silver.",
    ),
    Asset(
        symbol="NEAR",
        name="NEAR Protocol",
        asset_type=AssetType.CRYPTO,
        description="Sharded, developer-friendly blockchain for decentralized applications.",
    ),
    Asset(
        symbol="ARB",
        name="Arbitrum",
        asset_type=AssetType.CRYPTO,
        description="Leading Ethereum Layer 2 scaling solution using optimistic rollups.",
    ),
]


# =============================================================================
# Popular Stocks
# =============================================================================

POPULAR_STOCKS = [
    Asset(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=AssetType.STOCK,
        description="Technology company. iPhone, Mac, services ecosystem. Largest company by market cap.",
    ),
    Asset(
        symbol="MSFT",
        name="Microsoft Corporation",
        asset_type=AssetType.STOCK,
        description="Technology company. Windows, Azure cloud, Office 365, AI investments.",
    ),
    Asset(
        symbol="GOOGL",
        name="Alphabet Inc.",
        asset_type=AssetType.STOCK,
        description="Technology conglomerate. Google search, YouTube, cloud, AI research.",
    ),
    Asset(
        symbol="AMZN",
        name="Amazon.com Inc.",
        asset_type=AssetType.STOCK,
        description="E-commerce and cloud computing leader. AWS, retail, advertising.",
    ),
    Asset(
        symbol="NVDA",
        name="NVIDIA Corporation",
        asset_type=AssetType.STOCK,
        description="Semiconductor company. GPU leader, AI/ML hardware, data centers.",
    ),
    Asset(
        symbol="META",
        name="Meta Platforms Inc.",
        asset_type=AssetType.STOCK,
        description="Social media and technology. Facebook, Instagram, WhatsApp, metaverse.",
    ),
    Asset(
        symbol="TSLA",
        name="Tesla Inc.",
        asset_type=AssetType.STOCK,
        description="Electric vehicle and clean energy company. EVs, energy storage, solar.",
    ),
    Asset(
        symbol="BRK.B",
        name="Berkshire Hathaway",
        asset_type=AssetType.STOCK,
        description="Conglomerate holding company. Insurance, investments, diverse businesses.",
    ),
    Asset(
        symbol="JPM",
        name="JPMorgan Chase & Co.",
        asset_type=AssetType.STOCK,
        description="Largest US bank. Investment banking, retail banking, asset management.",
    ),
    Asset(
        symbol="V",
        name="Visa Inc.",
        asset_type=AssetType.STOCK,
        description="Global payments technology company. Credit/debit card network.",
    ),
    Asset(
        symbol="JNJ",
        name="Johnson & Johnson",
        asset_type=AssetType.STOCK,
        description="Healthcare conglomerate. Pharmaceuticals, medical devices, consumer health.",
    ),
    Asset(
        symbol="WMT",
        name="Walmart Inc.",
        asset_type=AssetType.STOCK,
        description="Largest retailer globally. Discount stores, e-commerce, grocery.",
    ),
    Asset(
        symbol="XOM",
        name="Exxon Mobil Corporation",
        asset_type=AssetType.STOCK,
        description="Largest US oil and gas company. Exploration, production, refining.",
    ),
    Asset(
        symbol="AMD",
        name="Advanced Micro Devices",
        asset_type=AssetType.STOCK,
        description="Semiconductor company. CPUs, GPUs, data center processors.",
    ),
    Asset(
        symbol="DIS",
        name="The Walt Disney Company",
        asset_type=AssetType.STOCK,
        description="Entertainment conglomerate. Theme parks, streaming, movies, TV.",
    ),
]


# =============================================================================
# Popular ETFs
# =============================================================================

POPULAR_ETFS = [
    Asset(
        symbol="SPY",
        name="SPDR S&P 500 ETF",
        asset_type=AssetType.ETF,
        description="Tracks S&P 500 index. Largest and most traded ETF.",
    ),
    Asset(
        symbol="QQQ",
        name="Invesco QQQ Trust",
        asset_type=AssetType.ETF,
        description="Tracks Nasdaq-100 index. Tech-heavy large-cap exposure.",
    ),
    Asset(
        symbol="VTI",
        name="Vanguard Total Stock Market ETF",
        asset_type=AssetType.ETF,
        description="Total US stock market exposure. Broad diversification.",
    ),
    Asset(
        symbol="IWM",
        name="iShares Russell 2000 ETF",
        asset_type=AssetType.ETF,
        description="Small-cap US stocks. Russell 2000 index tracker.",
    ),
    Asset(
        symbol="GLD",
        name="SPDR Gold Shares",
        asset_type=AssetType.ETF,
        description="Gold bullion ETF. Physical gold backing.",
    ),
]


# =============================================================================
# Asset Lookup
# =============================================================================

# Combined lookup dictionary
_ALL_ASSETS = {a.symbol.upper(): a for a in POPULAR_CRYPTOS + POPULAR_STOCKS + POPULAR_ETFS}


def get_asset_by_symbol(symbol: str) -> Asset | None:
    """
    Look up an asset by its symbol.

    Args:
        symbol: The trading symbol (case-insensitive)

    Returns:
        Asset if found, None otherwise
    """
    return _ALL_ASSETS.get(symbol.upper())


def search_assets(query: str) -> list[Asset]:
    """
    Search assets by symbol or name.

    Args:
        query: Search query

    Returns:
        List of matching assets
    """
    query = query.lower()
    results = []

    for asset in _ALL_ASSETS.values():
        if query in asset.symbol.lower() or query in asset.name.lower():
            results.append(asset)

    return results


def get_assets_by_type(asset_type: AssetType) -> list[Asset]:
    """Get all assets of a specific type."""
    return [a for a in _ALL_ASSETS.values() if a.asset_type == asset_type]


def create_custom_asset(
    symbol: str,
    name: str,
    asset_type: AssetType,
    description: str | None = None,
) -> Asset:
    """
    Create a custom asset for analysis.

    Args:
        symbol: Trading symbol
        name: Full name
        asset_type: Type of asset
        description: Optional description

    Returns:
        New Asset instance
    """
    return Asset(
        symbol=symbol.upper(),
        name=name,
        asset_type=asset_type,
        description=description or f"{name} ({symbol.upper()})",
    )
