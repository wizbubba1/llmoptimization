"""
Chart Generators for all modes.

- Mode A: Pie chart (Bullish vs Bearish)
- Mode B: Bar chart (model estimates)
- Mode C: Bar chart (repeated runs with mean/median)
- Mode D: Bar chart (Long vs Short)
"""

import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# Consistent dark theme for all charts
DARK_BG = "#2b2d31"  # Discord dark theme
DARK_TEXT = "#ffffff"
GRID_COLOR = "#40444b"

BULLISH_GREEN = "#2ecc71"
BEARISH_RED = "#e74c3c"
LONG_GREEN = "#2ecc71"
SHORT_RED = "#e74c3c"
BAR_BLUE = "#3498db"
MEDIAN_GREEN = "#2ecc71"
MEAN_RED = "#e74c3c"


def _setup_dark_theme(fig, ax):
    """Apply dark theme matching Discord."""
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)
    ax.tick_params(colors=DARK_TEXT)
    ax.xaxis.label.set_color(DARK_TEXT)
    ax.yaxis.label.set_color(DARK_TEXT)
    ax.title.set_color(DARK_TEXT)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)


def _save_to_buffer(fig) -> io.BytesIO:
    """Save figure to BytesIO buffer."""
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor(), edgecolor="none")
    buf.seek(0)
    plt.close(fig)
    return buf


def generate_sentiment_pie(
    bullish_count: int,
    bearish_count: int,
    unknown_count: int,
    title: str = "Bullish vs Bearish",
) -> io.BytesIO:
    """Generate pie chart for Mode A."""
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(DARK_BG)

    valid_total = bullish_count + bearish_count

    if valid_total == 0:
        ax.text(0.5, 0.5, "No valid responses", ha="center", va="center",
                fontsize=16, color=DARK_TEXT, transform=ax.transAxes)
        ax.set_facecolor(DARK_BG)
        return _save_to_buffer(fig)

    sizes = [bullish_count, bearish_count]
    labels = [
        f"BULLISH\n{bullish_count} models ({bullish_count/valid_total*100:.0f}%)",
        f"BEARISH\n{bearish_count} models ({bearish_count/valid_total*100:.0f}%)",
    ]
    colors = [BULLISH_GREEN, BEARISH_RED]
    explode = (0.05, 0.05)

    wedges, texts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        explode=explode,
        startangle=90,
        textprops={"fontsize": 13, "fontweight": "bold", "color": DARK_TEXT},
    )

    ax.set_title(title, fontsize=16, fontweight="bold", color=DARK_TEXT, pad=20)

    if unknown_count > 0:
        fig.text(0.5, 0.02, f"({unknown_count} model(s) did not respond)",
                 ha="center", fontsize=10, color="#888888")

    return _save_to_buffer(fig)


def generate_valuation_bars(
    model_names: list[str],
    values: list[float],
    median: float,
    mean: float,
    title: str = "Market Cap Estimates",
) -> io.BytesIO:
    """Generate horizontal bar chart for Mode B."""
    fig, ax = plt.subplots(figsize=(10, max(4, len(model_names) * 0.6 + 1)))
    _setup_dark_theme(fig, ax)

    if not values:
        ax.text(0.5, 0.5, "No valid estimates", ha="center", va="center",
                fontsize=14, color=DARK_TEXT)
        return _save_to_buffer(fig)

    # Sort by value
    pairs = sorted(zip(model_names, values), key=lambda x: x[1])
    names = [p[0] for p in pairs]
    vals = [p[1] for p in pairs]

    # Color by deviation from median
    colors = []
    for v in vals:
        pct_dev = abs(v - median) / median if median > 0 else 0
        if pct_dev <= 0.15:
            colors.append(BULLISH_GREEN)
        elif pct_dev <= 0.30:
            colors.append("#f39c12")
        else:
            colors.append(BEARISH_RED)

    y_pos = np.arange(len(names))
    bars = ax.barh(y_pos, vals, color=colors, edgecolor=GRID_COLOR, alpha=0.85)

    # Value labels on bars
    for bar, val in zip(bars, vals):
        if val >= 1:
            label = f"${val:.1f}B"
        else:
            label = f"${val * 1000:.0f}M"
        ax.text(bar.get_width() + max(vals) * 0.02, bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=9, color=DARK_TEXT)

    # Median and mean lines
    ax.axvline(median, color=MEDIAN_GREEN, linestyle="--", linewidth=2, alpha=0.8)
    ax.axvline(mean, color=MEAN_RED, linestyle=":", linewidth=2, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=10, color=DARK_TEXT)
    ax.set_xlabel("Market Cap (Billions USD)", fontsize=11)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)

    # Legend
    legend_elements = [
        mpatches.Patch(color=MEDIAN_GREEN, label=f"Median: ${median:.1f}B"),
        mpatches.Patch(color=MEAN_RED, label=f"Mean: ${mean:.1f}B"),
    ]
    legend = ax.legend(handles=legend_elements, loc="lower right", fontsize=9,
                       facecolor=DARK_BG, edgecolor=GRID_COLOR)
    for text in legend.get_texts():
        text.set_color(DARK_TEXT)

    ax.grid(True, axis="x", alpha=0.2, color=GRID_COLOR)
    ax.set_xlim(0, max(vals) * 1.15 if vals else 1)

    return _save_to_buffer(fig)


def generate_solo_bars(
    run_labels: list[str],
    values: list[float],
    median: float,
    mean: float,
    model_name: str,
    title: str = "Solo Valuation Runs",
) -> io.BytesIO:
    """Generate bar chart for Mode C (repeated runs)."""
    fig, ax = plt.subplots(figsize=(10, max(4, len(run_labels) * 0.7 + 1)))
    _setup_dark_theme(fig, ax)

    if not values:
        ax.text(0.5, 0.5, "No valid estimates", ha="center", va="center",
                fontsize=14, color=DARK_TEXT)
        return _save_to_buffer(fig)

    y_pos = np.arange(len(run_labels))
    bars = ax.barh(y_pos, values, color=BAR_BLUE, edgecolor=GRID_COLOR, alpha=0.85)

    # Value labels
    for bar, val in zip(bars, values):
        if val >= 1:
            label = f"${val:.1f}B"
        else:
            label = f"${val * 1000:.0f}M"
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=10, color=DARK_TEXT)

    # Median and mean lines
    ax.axvline(median, color=MEDIAN_GREEN, linestyle="--", linewidth=2, alpha=0.8)
    ax.axvline(mean, color=MEAN_RED, linestyle=":", linewidth=2, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(run_labels, fontsize=11, color=DARK_TEXT)
    ax.set_xlabel("Market Cap (Billions USD)", fontsize=11)
    ax.set_title(f"{title} - {model_name}", fontsize=14, fontweight="bold", pad=15)

    legend_elements = [
        mpatches.Patch(color=MEDIAN_GREEN, label=f"Median: ${median:.1f}B"),
        mpatches.Patch(color=MEAN_RED, label=f"Mean: ${mean:.1f}B"),
    ]
    legend = ax.legend(handles=legend_elements, loc="lower right", fontsize=9,
                       facecolor=DARK_BG, edgecolor=GRID_COLOR)
    for text in legend.get_texts():
        text.set_color(DARK_TEXT)

    ax.grid(True, axis="x", alpha=0.2, color=GRID_COLOR)
    ax.set_xlim(0, max(values) * 1.15 if values else 1)

    return _save_to_buffer(fig)


def generate_long_short_bars(
    long_count: int,
    short_count: int,
    model_results: list[tuple[str, str]],  # [(model_name, "LONG"/"SHORT"), ...]
    title: str = "Technical Analysis",
) -> io.BytesIO:
    """Generate bar chart for Mode D (Long vs Short)."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, max(4, len(model_results) * 0.5 + 1)),
                                    gridspec_kw={"width_ratios": [1, 2]})
    fig.patch.set_facecolor(DARK_BG)

    # Left: Summary bar
    ax1.set_facecolor(DARK_BG)
    categories = ["LONG", "SHORT"]
    counts = [long_count, short_count]
    bar_colors = [LONG_GREEN, SHORT_RED]

    bars = ax1.bar(categories, counts, color=bar_colors, edgecolor=GRID_COLOR, alpha=0.85, width=0.6)

    for bar, count in zip(bars, counts):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                 str(count), ha="center", va="bottom", fontsize=14,
                 fontweight="bold", color=DARK_TEXT)

    ax1.set_ylabel("Number of Models", fontsize=11, color=DARK_TEXT)
    ax1.set_title("Consensus", fontsize=13, fontweight="bold", color=DARK_TEXT, pad=10)
    ax1.tick_params(colors=DARK_TEXT)
    ax1.set_ylim(0, max(counts) * 1.3 if counts else 1)
    for spine in ax1.spines.values():
        spine.set_color(GRID_COLOR)

    # Right: Model-by-model breakdown
    ax2.set_facecolor(DARK_BG)

    if model_results:
        names = [r[0] for r in model_results]
        positions = [r[1] for r in model_results]
        colors = [LONG_GREEN if p == "LONG" else SHORT_RED if p == "SHORT" else "#888888"
                  for p in positions]
        x_vals = [1 if p == "LONG" else -1 if p == "SHORT" else 0 for p in positions]

        y_pos = np.arange(len(names))
        ax2.barh(y_pos, x_vals, color=colors, edgecolor=GRID_COLOR, alpha=0.85)

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names, fontsize=10, color=DARK_TEXT)
        ax2.set_xticks([-1, 0, 1])
        ax2.set_xticklabels(["SHORT", "", "LONG"], fontsize=10, color=DARK_TEXT)
        ax2.axvline(0, color=GRID_COLOR, linewidth=1)

    ax2.set_title("Model Breakdown", fontsize=13, fontweight="bold", color=DARK_TEXT, pad=10)
    ax2.tick_params(colors=DARK_TEXT)
    for spine in ax2.spines.values():
        spine.set_color(GRID_COLOR)

    fig.suptitle(title, fontsize=16, fontweight="bold", color=DARK_TEXT, y=1.02)
    plt.tight_layout()

    return _save_to_buffer(fig)
