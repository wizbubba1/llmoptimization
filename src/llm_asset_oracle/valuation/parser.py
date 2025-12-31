"""
Market Cap Parser

Extracts market cap values from LLM responses.
Handles various formats:
- "$10B", "$10 billion", "$10,000,000,000"
- "10B", "10 billion", "10bn"
- "$500M", "$500 million", "500m"
- "1.5T", "1.5 trillion"
- Written out: "ten billion dollars"
"""

import re
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MarketCapResult:
    """Result of parsing a market cap from LLM response."""

    value_billions: Optional[float]  # Normalized to billions
    raw_text: str  # The extracted text that was parsed
    confidence: float  # 0-1, how confident we are in the parse
    model_name: str
    model_id: str
    full_response: str
    error: Optional[str] = None

    @property
    def value_formatted(self) -> str:
        """Return nicely formatted value."""
        if self.value_billions is None:
            return "N/A"

        if self.value_billions >= 1000:
            return f"${self.value_billions / 1000:.2f}T"
        elif self.value_billions >= 1:
            return f"${self.value_billions:.1f}B"
        else:
            return f"${self.value_billions * 1000:.0f}M"

    @property
    def value_raw(self) -> float:
        """Return raw value in billions, or 0 if None."""
        return self.value_billions if self.value_billions is not None else 0


# Multipliers for different suffixes
MULTIPLIERS = {
    # Trillions
    't': 1000,
    'T': 1000,
    'trillion': 1000,
    'trillions': 1000,
    'tn': 1000,

    # Billions
    'b': 1,
    'B': 1,
    'billion': 1,
    'billions': 1,
    'bn': 1,

    # Millions
    'm': 0.001,
    'M': 0.001,
    'million': 0.001,
    'millions': 0.001,
    'mn': 0.001,
    'mm': 0.001,

    # Thousands (rare but possible)
    'k': 0.000001,
    'K': 0.000001,
    'thousand': 0.000001,
    'thousands': 0.000001,
}

# Word numbers
WORD_NUMBERS = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'fifteen': 15,
    'twenty': 20,
    'thirty': 30,
    'forty': 40,
    'fifty': 50,
    'sixty': 60,
    'seventy': 70,
    'eighty': 80,
    'ninety': 90,
    'hundred': 100,
}


def parse_market_cap(
    response: str,
    model_name: str = "Unknown",
    model_id: str = "unknown",
) -> MarketCapResult:
    """
    Parse market cap value from an LLM response.

    Args:
        response: The full LLM response text
        model_name: Name of the model for tracking
        model_id: ID of the model

    Returns:
        MarketCapResult with parsed value or error
    """
    if not response or not response.strip():
        return MarketCapResult(
            value_billions=None,
            raw_text="",
            confidence=0.0,
            model_name=model_name,
            model_id=model_id,
            full_response=response,
            error="Empty response",
        )

    # Try different parsing strategies in order of reliability
    strategies = [
        _parse_dollar_with_suffix,      # "$10B", "$10 billion"
        _parse_number_with_suffix,      # "10B", "10 billion"
        _parse_full_number,             # "$10,000,000,000"
        _parse_word_number,             # "ten billion"
        _parse_range_take_midpoint,     # "$10-20B" -> $15B
    ]

    for strategy in strategies:
        result = strategy(response)
        if result is not None:
            value, raw_text, confidence = result
            return MarketCapResult(
                value_billions=value,
                raw_text=raw_text,
                confidence=confidence,
                model_name=model_name,
                model_id=model_id,
                full_response=response,
            )

    # No valid parse found
    return MarketCapResult(
        value_billions=None,
        raw_text="",
        confidence=0.0,
        model_name=model_name,
        model_id=model_id,
        full_response=response,
        error="Could not parse market cap from response",
    )


def _parse_dollar_with_suffix(text: str) -> Optional[Tuple[float, str, float]]:
    """
    Parse patterns like "$10B", "$10 billion", "$10.5B"
    """
    # Pattern: $[number][optional space][suffix]
    pattern = r'\$\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|bn|mn|[tbmTBM])\b'

    matches = re.findall(pattern, text, re.IGNORECASE)

    if matches:
        # Take the first match (usually the main estimate)
        number_str, suffix = matches[0]
        number = float(number_str)
        suffix_lower = suffix.lower()

        # Get multiplier
        multiplier = MULTIPLIERS.get(suffix_lower, 1)
        value_billions = number * multiplier

        raw_text = f"${number_str}{suffix}"
        return (value_billions, raw_text, 0.95)

    return None


def _parse_number_with_suffix(text: str) -> Optional[Tuple[float, str, float]]:
    """
    Parse patterns like "10B", "10 billion" (without dollar sign)
    """
    # Pattern: [number][optional space][suffix]
    pattern = r'(\d+(?:\.\d+)?)\s*(trillion|billion|million|bn|mn|[tbmTBM])\b'

    matches = re.findall(pattern, text, re.IGNORECASE)

    if matches:
        number_str, suffix = matches[0]
        number = float(number_str)
        suffix_lower = suffix.lower()

        multiplier = MULTIPLIERS.get(suffix_lower, 1)
        value_billions = number * multiplier

        raw_text = f"{number_str}{suffix}"
        return (value_billions, raw_text, 0.85)

    return None


def _parse_full_number(text: str) -> Optional[Tuple[float, str, float]]:
    """
    Parse full numbers like "$10,000,000,000" or "10000000000"
    """
    # Pattern: optional $ followed by large number with commas
    pattern = r'\$?\s*(\d{1,3}(?:,\d{3})+|\d{9,})'

    matches = re.findall(pattern, text)

    if matches:
        number_str = matches[0].replace(',', '')
        number = float(number_str)

        # Convert to billions
        value_billions = number / 1_000_000_000

        # Only accept if it's in a reasonable range (100M to 10T)
        if 0.1 <= value_billions <= 10000:
            raw_text = matches[0]
            return (value_billions, raw_text, 0.80)

    return None


def _parse_word_number(text: str) -> Optional[Tuple[float, str, float]]:
    """
    Parse written numbers like "ten billion" or "fifty billion dollars"
    """
    text_lower = text.lower()

    # Look for patterns like "X billion" or "X trillion"
    for suffix, multiplier in [('trillion', 1000), ('billion', 1)]:
        pattern = rf'(\w+(?:\s+\w+)?)\s+{suffix}'
        matches = re.findall(pattern, text_lower)

        for match in matches:
            words = match.strip().split()
            number = _words_to_number(words)
            if number is not None:
                value_billions = number * multiplier
                raw_text = f"{match} {suffix}"
                return (value_billions, raw_text, 0.70)

    return None


def _words_to_number(words: list) -> Optional[float]:
    """Convert word numbers to float."""
    total = 0
    current = 0

    for word in words:
        word = word.lower().strip()

        if word in WORD_NUMBERS:
            val = WORD_NUMBERS[word]
            if val == 100:
                current *= 100
            else:
                current += val
        elif word == 'and':
            continue
        else:
            # Try to parse as a digit
            try:
                current += float(word)
            except ValueError:
                return None

    total += current
    return total if total > 0 else None


def _parse_range_take_midpoint(text: str) -> Optional[Tuple[float, str, float]]:
    """
    Parse ranges like "$10-20B" or "$10 to $20 billion" and take midpoint.
    """
    # Pattern: $X-Y[suffix] or $X to $Y [suffix]
    patterns = [
        r'\$(\d+(?:\.\d+)?)\s*[-–to]+\s*\$?(\d+(?:\.\d+)?)\s*(trillion|billion|million|bn|[tbmTBM])',
        r'(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|bn|[tbmTBM])',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            low_str, high_str, suffix = matches[0]
            low = float(low_str)
            high = float(high_str)
            midpoint = (low + high) / 2

            suffix_lower = suffix.lower()
            multiplier = MULTIPLIERS.get(suffix_lower, 1)
            value_billions = midpoint * multiplier

            raw_text = f"{low_str}-{high_str}{suffix}"
            return (value_billions, raw_text, 0.75)

    return None


def extract_all_market_caps(text: str) -> list[Tuple[float, str]]:
    """
    Extract ALL market cap mentions from text (for analysis).

    Returns:
        List of (value_in_billions, raw_text) tuples
    """
    results = []

    # Try all patterns
    strategies = [
        (_parse_dollar_with_suffix, text),
        (_parse_number_with_suffix, text),
    ]

    # Find all matches with dollar suffix pattern
    pattern = r'\$\s*(\d+(?:\.\d+)?)\s*(trillion|billion|million|bn|mn|[tbmTBM])\b'
    for match in re.finditer(pattern, text, re.IGNORECASE):
        number = float(match.group(1))
        suffix = match.group(2).lower()
        multiplier = MULTIPLIERS.get(suffix, 1)
        value = number * multiplier
        results.append((value, match.group(0)))

    return results


# Testing
if __name__ == "__main__":
    test_cases = [
        "I estimate the market cap to be around $45 billion.",
        "My best estimate is $10B",
        "The market cap could reach $1.5 trillion",
        "Somewhere between $20-30 billion seems reasonable",
        "I'd say approximately 15bn",
        "Around fifty billion dollars",
        "$10,000,000,000 is my estimate",
        "Market cap: 500M",
        "The valuation is $8.5B",
    ]

    print("=== Market Cap Parser Tests ===\n")
    for test in test_cases:
        result = parse_market_cap(test, "TestModel", "test")
        print(f"Input: {test}")
        print(f"Parsed: {result.value_formatted} (raw: {result.raw_text}, conf: {result.confidence})")
        print()
