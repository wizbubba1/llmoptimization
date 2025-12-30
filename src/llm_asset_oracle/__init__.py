"""
LLM Asset Oracle - A Scientific Trading Tool

This application aggregates sentiment analysis from multiple Large Language Models
to identify assets (stocks, cryptocurrencies, etc.) that have consistent positive
ratings across different AI systems.

The core methodology:
1. Query multiple LLMs with standardized prompts about specific assets
2. Extract structured sentiment scores using consistent parsing
3. Apply statistical analysis to measure consensus and confidence
4. Rank assets by their "LLM Optimization Score" (LOS)

Copyright 2024 LLM Asset Oracle Team
Licensed under the MIT License
"""

__version__ = "1.0.0"
__author__ = "LLM Asset Oracle Team"

from llm_asset_oracle.core.models import Asset, AssetType, LLMResponse, ConsensusScore
from llm_asset_oracle.core.oracle import LLMAssetOracle

__all__ = [
    "Asset",
    "AssetType",
    "LLMResponse",
    "ConsensusScore",
    "LLMAssetOracle",
    "__version__",
]
