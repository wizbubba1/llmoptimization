"""Data models for LLM Asset Oracle."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Types of tradeable assets."""

    CRYPTO = "crypto"
    STOCK = "stock"
    ETF = "etf"
    FOREX = "forex"
    COMMODITY = "commodity"
    INDEX = "index"


class Asset(BaseModel):
    """Represents a tradeable asset."""

    symbol: str = Field(..., description="Trading symbol (e.g., BTC, AAPL)")
    name: str = Field(..., description="Full asset name")
    asset_type: AssetType = Field(..., description="Type of asset")
    description: Optional[str] = Field(default=None, description="Asset description")
    market_cap: Optional[float] = Field(default=None, description="Market capitalization in USD")
    current_price: Optional[float] = Field(default=None, description="Current price in USD")
    price_change_24h: Optional[float] = Field(default=None, description="24h price change %")
    volume_24h: Optional[float] = Field(default=None, description="24h trading volume")

    class Config:
        use_enum_values = True


class SentimentRating(BaseModel):
    """Structured sentiment rating from an LLM."""

    # Core ratings (1-10 scale)
    overall_score: float = Field(..., ge=1, le=10, description="Overall investment rating")
    bullish_score: float = Field(..., ge=1, le=10, description="Bullish sentiment strength")
    risk_score: float = Field(..., ge=1, le=10, description="Risk level (10=highest risk)")

    # Timeframe ratings
    short_term_outlook: float = Field(..., ge=1, le=10, description="1-30 day outlook")
    medium_term_outlook: float = Field(..., ge=1, le=10, description="1-6 month outlook")
    long_term_outlook: float = Field(..., ge=1, le=10, description="1+ year outlook")

    # Qualitative factors
    fundamentals_score: float = Field(..., ge=1, le=10, description="Fundamental strength")
    momentum_score: float = Field(..., ge=1, le=10, description="Technical momentum")
    sentiment_score: float = Field(..., ge=1, le=10, description="Market sentiment")

    # Reasoning
    key_bullish_factors: list[str] = Field(default_factory=list, description="Bullish catalysts")
    key_bearish_factors: list[str] = Field(default_factory=list, description="Bearish concerns")
    summary: str = Field(..., description="Brief analysis summary")


class LLMResponse(BaseModel):
    """Response from a single LLM query."""

    provider: str = Field(..., description="LLM provider name")
    model: str = Field(..., description="Specific model used")
    asset_symbol: str = Field(..., description="Asset that was analyzed")
    rating: SentimentRating = Field(..., description="Structured rating")
    raw_response: str = Field(..., description="Raw LLM response text")
    query_timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: float = Field(..., description="Query latency in milliseconds")
    tokens_used: Optional[int] = Field(default=None, description="Total tokens consumed")

    @property
    def composite_score(self) -> float:
        """Calculate weighted composite score."""
        weights = {
            "overall": 0.25,
            "short_term": 0.15,
            "medium_term": 0.20,
            "long_term": 0.15,
            "fundamentals": 0.10,
            "momentum": 0.10,
            "sentiment": 0.05,
        }

        # Invert risk score (lower risk = better)
        risk_adjusted = 10 - self.rating.risk_score

        score = (
            self.rating.overall_score * weights["overall"]
            + self.rating.short_term_outlook * weights["short_term"]
            + self.rating.medium_term_outlook * weights["medium_term"]
            + self.rating.long_term_outlook * weights["long_term"]
            + self.rating.fundamentals_score * weights["fundamentals"]
            + self.rating.momentum_score * weights["momentum"]
            + self.rating.sentiment_score * weights["sentiment"]
        )

        # Apply risk adjustment (reduce score for high-risk assets)
        risk_multiplier = 0.5 + (risk_adjusted / 20)  # 0.5 to 1.0
        return score * risk_multiplier


class ConsensusMetrics(BaseModel):
    """Statistical metrics for consensus calculation."""

    mean: float = Field(..., description="Mean score across models")
    median: float = Field(..., description="Median score")
    std_dev: float = Field(..., description="Standard deviation")
    min_score: float = Field(..., description="Minimum score")
    max_score: float = Field(..., description="Maximum score")
    range: float = Field(..., description="Score range (max - min)")
    coefficient_of_variation: float = Field(..., description="CV = std_dev / mean")
    interquartile_range: float = Field(..., description="IQR for outlier detection")


class ConsensusScore(BaseModel):
    """Aggregated consensus score from multiple LLMs."""

    asset: Asset = Field(..., description="The analyzed asset")
    responses: list[LLMResponse] = Field(..., description="Individual LLM responses")

    # Aggregated scores
    los_score: float = Field(..., ge=0, le=100, description="LLM Optimization Score (0-100)")
    consensus_strength: float = Field(
        ..., ge=0, le=100, description="How much models agree (0-100)"
    )
    confidence_interval: tuple[float, float] = Field(
        ..., description="95% confidence interval for LOS"
    )

    # Detailed metrics
    metrics: ConsensusMetrics = Field(..., description="Statistical metrics")

    # Breakdown by category
    category_scores: dict[str, float] = Field(
        default_factory=dict, description="Scores by category"
    )

    # Model agreement
    bullish_models: int = Field(..., description="Models with bullish outlook (>6)")
    bearish_models: int = Field(..., description="Models with bearish outlook (<5)")
    neutral_models: int = Field(..., description="Models with neutral outlook (5-6)")

    # Aggregated insights
    common_bullish_factors: list[str] = Field(
        default_factory=list, description="Frequently mentioned bullish factors"
    )
    common_bearish_factors: list[str] = Field(
        default_factory=list, description="Frequently mentioned bearish factors"
    )

    # Metadata
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_models_queried: int = Field(..., description="Number of models used")
    total_latency_ms: float = Field(..., description="Total query time")

    @property
    def recommendation(self) -> str:
        """Generate recommendation based on LOS score."""
        if self.los_score >= 80:
            return "STRONG BUY"
        elif self.los_score >= 65:
            return "BUY"
        elif self.los_score >= 50:
            return "HOLD"
        elif self.los_score >= 35:
            return "SELL"
        else:
            return "STRONG SELL"

    @property
    def consensus_label(self) -> str:
        """Label for consensus strength."""
        if self.consensus_strength >= 80:
            return "Very High Consensus"
        elif self.consensus_strength >= 60:
            return "High Consensus"
        elif self.consensus_strength >= 40:
            return "Moderate Consensus"
        elif self.consensus_strength >= 20:
            return "Low Consensus"
        else:
            return "No Consensus"


class AnalysisResult(BaseModel):
    """Complete analysis result for an asset."""

    consensus: ConsensusScore = Field(..., description="Consensus analysis")
    market_data: Optional[dict] = Field(default=None, description="Current market data")
    historical_scores: list[float] = Field(
        default_factory=list, description="Previous LOS scores"
    )
    score_trend: Optional[str] = Field(default=None, description="Trend direction")

    class Config:
        arbitrary_types_allowed = True
