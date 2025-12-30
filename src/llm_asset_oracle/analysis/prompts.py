"""Standardized prompt templates for consistent LLM analysis."""

from llm_asset_oracle.core.models import Asset, AssetType


class PromptTemplates:
    """
    Standardized prompt templates for asset analysis.

    These prompts are designed to:
    1. Elicit consistent, structured responses across different LLMs
    2. Cover multiple analysis dimensions (fundamental, technical, sentiment)
    3. Request specific numerical ratings for quantitative comparison
    4. Be neutral and avoid leading the model toward any bias
    """

    SYSTEM_PROMPT = """You are a professional financial analyst AI assistant. Your role is to provide objective, data-driven analysis of investment assets.

IMPORTANT GUIDELINES:
1. Be objective and balanced - present both bullish and bearish perspectives
2. Base your analysis on publicly available information and general market knowledge
3. Provide specific numerical ratings as requested
4. Do not make specific price predictions
5. Always include risk considerations
6. Format your response as valid JSON when requested

DISCLAIMER: Your analysis is for informational purposes only and does not constitute financial advice."""

    ASSET_ANALYSIS_TEMPLATE = """Analyze the following asset and provide a comprehensive investment assessment.

## Asset Information
- **Symbol**: {symbol}
- **Name**: {name}
- **Type**: {asset_type}
- **Description**: {description}
{market_data_section}

## Analysis Request
Please analyze this asset across multiple dimensions and provide your assessment in the following JSON format:

```json
{{
    "overall_score": <1-10 rating of overall investment attractiveness>,
    "bullish_score": <1-10 rating of bullish sentiment strength>,
    "risk_score": <1-10 rating of risk level, where 10 is highest risk>,
    "short_term_outlook": <1-10 rating for 1-30 day outlook>,
    "medium_term_outlook": <1-10 rating for 1-6 month outlook>,
    "long_term_outlook": <1-10 rating for 1+ year outlook>,
    "fundamentals_score": <1-10 rating of fundamental strength>,
    "momentum_score": <1-10 rating of technical/price momentum>,
    "sentiment_score": <1-10 rating of current market sentiment>,
    "key_bullish_factors": ["factor1", "factor2", "factor3"],
    "key_bearish_factors": ["factor1", "factor2", "factor3"],
    "summary": "<2-3 sentence summary of your analysis>"
}}
```

## Rating Guidelines
- **1-3**: Very negative/weak/bearish
- **4-5**: Somewhat negative/below average
- **5-6**: Neutral/average
- **6-7**: Somewhat positive/above average
- **8-10**: Very positive/strong/bullish

For risk_score specifically:
- **1-3**: Low risk, stable asset
- **4-6**: Moderate risk
- **7-10**: High risk, volatile asset

Please provide your analysis based on your knowledge cutoff date. Focus on fundamental factors, market dynamics, competitive positioning, and overall investment merit.

Respond ONLY with the JSON object, no additional text."""

    COMPARISON_TEMPLATE = """Compare the following two assets for investment purposes.

## Asset 1
- **Symbol**: {symbol1}
- **Name**: {name1}
- **Type**: {type1}

## Asset 2
- **Symbol**: {symbol2}
- **Name**: {name2}
- **Type**: {type2}

Please provide a comparative analysis in the following JSON format:

```json
{{
    "preferred_asset": "<symbol of the asset you would prefer>",
    "preference_strength": <1-10 how strongly you prefer it>,
    "asset1_score": <1-10 overall score for asset 1>,
    "asset2_score": <1-10 overall score for asset 2>,
    "asset1_strengths": ["strength1", "strength2"],
    "asset2_strengths": ["strength1", "strength2"],
    "asset1_weaknesses": ["weakness1", "weakness2"],
    "asset2_weaknesses": ["weakness1", "weakness2"],
    "comparison_summary": "<2-3 sentence comparison summary>"
}}
```

Respond ONLY with the JSON object."""

    QUICK_SENTIMENT_TEMPLATE = """Rate the investment sentiment for {symbol} ({name}) on a scale of 1-10.

Consider: fundamentals, market position, growth potential, risks, and current market conditions.

Respond in this exact format:
```json
{{
    "symbol": "{symbol}",
    "overall_score": <1-10>,
    "risk_score": <1-10>,
    "one_line_summary": "<brief assessment>"
}}
```"""

    MARKET_CONTEXT_TEMPLATE = """Given the current market environment, analyze {symbol} ({name}).

Current Context:
{market_context}

Provide your analysis as JSON with overall_score (1-10), risk_score (1-10), market_alignment_score (1-10, how well this asset fits current conditions), and a brief summary."""

    @classmethod
    def format_asset_analysis(cls, asset: Asset) -> str:
        """
        Format the asset analysis prompt for a given asset.

        Args:
            asset: The asset to analyze

        Returns:
            Formatted prompt string
        """
        # Build market data section if available
        market_data_section = ""
        if asset.current_price is not None:
            market_data_section += f"\n## Current Market Data\n"
            market_data_section += f"- **Current Price**: ${asset.current_price:,.2f}\n"
            if asset.price_change_24h is not None:
                change_sign = "+" if asset.price_change_24h >= 0 else ""
                market_data_section += (
                    f"- **24h Change**: {change_sign}{asset.price_change_24h:.2f}%\n"
                )
            if asset.market_cap is not None:
                market_data_section += f"- **Market Cap**: ${asset.market_cap:,.0f}\n"
            if asset.volume_24h is not None:
                market_data_section += f"- **24h Volume**: ${asset.volume_24h:,.0f}\n"

        return cls.ASSET_ANALYSIS_TEMPLATE.format(
            symbol=asset.symbol,
            name=asset.name,
            asset_type=asset.asset_type.value if isinstance(asset.asset_type, AssetType) else asset.asset_type,
            description=asset.description or "No description available",
            market_data_section=market_data_section,
        )

    @classmethod
    def format_comparison(cls, asset1: Asset, asset2: Asset) -> str:
        """Format comparison prompt for two assets."""
        return cls.COMPARISON_TEMPLATE.format(
            symbol1=asset1.symbol,
            name1=asset1.name,
            type1=asset1.asset_type.value if isinstance(asset1.asset_type, AssetType) else asset1.asset_type,
            symbol2=asset2.symbol,
            name2=asset2.name,
            type2=asset2.asset_type.value if isinstance(asset2.asset_type, AssetType) else asset2.asset_type,
        )

    @classmethod
    def format_quick_sentiment(cls, asset: Asset) -> str:
        """Format quick sentiment check prompt."""
        return cls.QUICK_SENTIMENT_TEMPLATE.format(
            symbol=asset.symbol,
            name=asset.name,
        )

    @classmethod
    def format_with_context(cls, asset: Asset, market_context: str) -> str:
        """Format analysis prompt with market context."""
        return cls.MARKET_CONTEXT_TEMPLATE.format(
            symbol=asset.symbol,
            name=asset.name,
            market_context=market_context,
        )
