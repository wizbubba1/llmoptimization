"""
Chart Generator for Valuation Analysis

Generates visual charts:
- Histogram of valuations
- Boxplot
- Model comparison bar chart
"""

import io
from typing import Optional
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from llm_asset_oracle.valuation.statistics import ValuationStatistics
from llm_asset_oracle.valuation.parser import MarketCapResult


def generate_valuation_chart(
    stats: ValuationStatistics,
    show_models: bool = True,
) -> io.BytesIO:
    """
    Generate a comprehensive valuation chart.

    Creates a figure with:
    - Left: Histogram of valuations
    - Right: Box plot + individual model points

    Args:
        stats: ValuationStatistics with all data
        show_models: Whether to show individual model labels

    Returns:
        BytesIO buffer containing PNG image
    """
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        f'LLM Valuation Consensus: {stats.token_name} ({stats.ticker}) - {stats.target_year}',
        fontsize=14,
        fontweight='bold'
    )

    values = stats.valid_estimates

    if len(values) == 0:
        ax1.text(0.5, 0.5, 'No valid estimates', ha='center', va='center', fontsize=14)
        ax2.text(0.5, 0.5, 'No valid estimates', ha='center', va='center', fontsize=14)
    else:
        # === LEFT: Histogram ===
        _draw_histogram(ax1, values, stats)

        # === RIGHT: Model Bar Chart ===
        _draw_model_bars(ax2, stats, show_models)

    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return buf


def _draw_histogram(ax, values: list[float], stats: ValuationStatistics):
    """Draw histogram of valuations."""
    # Determine number of bins
    n_bins = min(max(5, len(values) // 2), 15)

    # Create histogram
    counts, bins, patches = ax.hist(
        values,
        bins=n_bins,
        color='#3498db',
        edgecolor='white',
        alpha=0.7,
    )

    # Add mean and median lines
    ax.axvline(stats.mean_value, color='#e74c3c', linestyle='--',
               linewidth=2, label=f'Mean: ${stats.mean_value:.1f}B')
    ax.axvline(stats.median_value, color='#2ecc71', linestyle='-',
               linewidth=2, label=f'Median: ${stats.median_value:.1f}B')

    # Add IQR shading
    ax.axvspan(stats.q1, stats.q3, alpha=0.2, color='green',
               label=f'IQR: ${stats.q1:.1f}B - ${stats.q3:.1f}B')

    ax.set_xlabel('Valuation (Billions USD)', fontsize=11)
    ax.set_ylabel('Frequency', fontsize=11)
    ax.set_title('Distribution of LLM Estimates', fontsize=12, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)

    # Format x-axis
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}B'))

    # Add grid
    ax.grid(True, alpha=0.3)


def _draw_model_bars(ax, stats: ValuationStatistics, show_labels: bool):
    """Draw horizontal bar chart of each model's estimate."""
    # Filter to valid estimates only
    valid_estimates = [e for e in stats.estimates if e.value_billions is not None and e.value_billions > 0]

    if not valid_estimates:
        ax.text(0.5, 0.5, 'No valid estimates', ha='center', va='center')
        return

    # Sort by value
    sorted_estimates = sorted(valid_estimates, key=lambda x: x.value_billions)

    models = [e.model_name for e in sorted_estimates]
    values = [e.value_billions for e in sorted_estimates]

    # Color coding based on deviation from median
    colors = []
    for v in values:
        diff_pct = abs(v - stats.median_value) / stats.median_value if stats.median_value > 0 else 0
        if diff_pct <= 0.15:
            colors.append('#2ecc71')  # Green - close to median
        elif diff_pct <= 0.30:
            colors.append('#f39c12')  # Orange - moderate deviation
        else:
            colors.append('#e74c3c')  # Red - outlier

    y_pos = np.arange(len(models))

    # Draw bars
    bars = ax.barh(y_pos, values, color=colors, edgecolor='white', alpha=0.8)

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2,
                f'${val:.1f}B', va='center', fontsize=9)

    # Add median line
    ax.axvline(stats.median_value, color='#2ecc71', linestyle='--',
               linewidth=2, alpha=0.8)
    ax.axvline(stats.mean_value, color='#e74c3c', linestyle=':',
               linewidth=2, alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(models, fontsize=9)
    ax.set_xlabel('Valuation (Billions USD)', fontsize=11)
    ax.set_title('Model-by-Model Estimates', fontsize=12, fontweight='bold')

    # Legend for colors
    legend_elements = [
        mpatches.Patch(color='#2ecc71', label='Within 15% of median'),
        mpatches.Patch(color='#f39c12', label='15-30% deviation'),
        mpatches.Patch(color='#e74c3c', label='>30% deviation (outlier)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=8)

    ax.grid(True, axis='x', alpha=0.3)


def generate_simple_boxplot(
    stats: ValuationStatistics,
) -> io.BytesIO:
    """Generate a simple boxplot chart."""
    fig, ax = plt.subplots(figsize=(8, 6))

    values = stats.valid_estimates

    if len(values) < 2:
        ax.text(0.5, 0.5, 'Need at least 2 estimates for boxplot',
                ha='center', va='center', fontsize=12)
    else:
        bp = ax.boxplot(values, vert=True, patch_artist=True)

        # Style the boxplot
        bp['boxes'][0].set_facecolor('#3498db')
        bp['boxes'][0].set_alpha(0.7)
        bp['medians'][0].set_color('#2ecc71')
        bp['medians'][0].set_linewidth(2)

        # Add individual points
        x = np.random.normal(1, 0.04, size=len(values))
        ax.scatter(x, values, alpha=0.6, color='#e74c3c', s=50, zorder=5)

        # Labels
        ax.set_ylabel('Valuation (Billions USD)', fontsize=11)
        ax.set_title(
            f'{stats.token_name} ({stats.ticker}) - LLM Valuations',
            fontsize=12,
            fontweight='bold'
        )

        # Stats text
        stats_text = (
            f"Median: ${stats.median_value:.1f}B\n"
            f"Mean: ${stats.mean_value:.1f}B\n"
            f"Std Dev: ${stats.std_dev:.1f}B\n"
            f"Consensus: {stats.consensus_strength:.0f}%"
        )
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}B'))
        ax.grid(True, alpha=0.3)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return buf


def generate_comparison_chart(
    stats_list: list[ValuationStatistics],
) -> io.BytesIO:
    """
    Generate a comparison chart for multiple tokens.

    Args:
        stats_list: List of ValuationStatistics for different tokens

    Returns:
        BytesIO buffer containing PNG image
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    tokens = [s.ticker for s in stats_list]
    means = [s.mean_value for s in stats_list]
    medians = [s.median_value for s in stats_list]
    errors = [[s.median_value - s.q1 for s in stats_list],
              [s.q3 - s.median_value for s in stats_list]]

    x = np.arange(len(tokens))
    width = 0.35

    bars1 = ax.bar(x - width/2, means, width, label='Mean', color='#3498db', alpha=0.7)
    bars2 = ax.bar(x + width/2, medians, width, label='Median', color='#2ecc71', alpha=0.7,
                   yerr=errors, capsize=5)

    ax.set_ylabel('Valuation (Billions USD)', fontsize=11)
    ax.set_title('LLM Valuation Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(tokens)
    ax.legend()

    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:.0f}B'))
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return buf
