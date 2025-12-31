"""
Valuation Prompt Template System

Creates consistent, factual prompts for LLM market cap estimation.
Based on the proven format:
"Year is 2026. Consider {token} ({ticker}): {description}. Given {factors},
what is its best-estimate market cap (not FDV)? Do not use web search."
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ValuationPrompt:
    """
    Data class holding all fields for a valuation prompt.

    This ensures consistent structure across all valuations.
    """
    token_name: str
    ticker: str
    year: int
    category: str  # e.g., "Layer 1", "DeFi protocol", "Infrastructure"
    description: str  # One-line description of what it does
    key_differentiator: str  # What makes it unique/special
    factors: str  # What to consider (risks, competition, etc.)

    # Optional fields
    comparable_projects: Optional[str] = None  # e.g., "similar to Solana but..."
    additional_context: Optional[str] = None  # Any extra info


# The core template - proven to work well with LLMs
# Now includes instruction for concise final answer
VALUATION_TEMPLATE = """Year is {year}. Consider {token_name} ({ticker}): {category_description}. {key_differentiator}. Given {factors}, what is its best-estimate market cap (not FDV)? Do not use web search.

IMPORTANT: End your response with a single line in this exact format:
VERDICT: $[X]B - [one sentence reasoning]"""

# Extended template with comparables
VALUATION_TEMPLATE_WITH_COMPARABLES = """Year is {year}. Consider {token_name} ({ticker}): {category_description}. {key_differentiator}. {comparable_context}Given {factors}, what is its best-estimate market cap (not FDV)? Do not use web search.

IMPORTANT: End your response with a single line in this exact format:
VERDICT: $[X]B - [one sentence reasoning]"""


def build_valuation_prompt(prompt_data: ValuationPrompt) -> str:
    """
    Build the final prompt string from ValuationPrompt data.

    Args:
        prompt_data: ValuationPrompt with all fields filled

    Returns:
        Complete prompt string ready to send to LLMs
    """
    # Combine category and description
    if prompt_data.category:
        category_description = f"a {prompt_data.category} {prompt_data.description}"
    else:
        category_description = prompt_data.description

    # Handle optional comparable projects
    if prompt_data.comparable_projects:
        comparable_context = f"Comparable to {prompt_data.comparable_projects}. "
        template = VALUATION_TEMPLATE_WITH_COMPARABLES
    else:
        comparable_context = ""
        template = VALUATION_TEMPLATE

    # Build the prompt
    prompt = template.format(
        year=prompt_data.year,
        token_name=prompt_data.token_name,
        ticker=prompt_data.ticker,
        category_description=category_description,
        key_differentiator=prompt_data.key_differentiator,
        comparable_context=comparable_context,
        factors=prompt_data.factors,
    )

    # Add any additional context
    if prompt_data.additional_context:
        prompt = f"{prompt_data.additional_context}\n\n{prompt}"

    return prompt


def build_simple_prompt(
    token_name: str,
    ticker: str,
    year: int,
    description: str,
    differentiator: str,
    factors: str,
) -> str:
    """
    Simplified prompt builder for quick use.

    Args:
        token_name: Name of the token
        ticker: Ticker symbol
        year: Target year for valuation
        description: What the project does
        differentiator: What makes it unique
        factors: What to consider

    Returns:
        Complete prompt string
    """
    prompt_data = ValuationPrompt(
        token_name=token_name,
        ticker=ticker,
        year=year,
        category="",
        description=description,
        key_differentiator=differentiator,
        factors=factors,
    )
    return build_valuation_prompt(prompt_data)


# =============================================================================
# EXAMPLE PROMPTS (for reference/testing)
# =============================================================================

EXAMPLE_POST_FIAT = ValuationPrompt(
    token_name="Post Fiat",
    ticker="PF",
    year=2026,
    category="",
    description="a new version of XRP that is decentralized via AI selecting the unique node list fairly",
    key_differentiator="its use case is the investment bank not the transaction bank, which has far less compliance issues than replacing SWIFT",
    factors="decentralization, regulatory clarity, institutional adoption potential",
)

EXAMPLE_MONAD = ValuationPrompt(
    token_name="Monad",
    ticker="MON",
    year=2026,
    category="high-throughput EVM Layer-1",
    description="using parallel execution for low-latency DeFi and consumer apps",
    key_differentiator="mainnet matured after late-2025 launch and major funding",
    factors="performance, adoption risks, and L1 competition",
)


if __name__ == "__main__":
    # Test the prompt builder
    print("=== Post Fiat Prompt ===")
    print(build_valuation_prompt(EXAMPLE_POST_FIAT))
    print()
    print("=== Monad Prompt ===")
    print(build_valuation_prompt(EXAMPLE_MONAD))
