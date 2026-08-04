#!/usr/bin/env -S uv --quiet run --active --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas>=2.0.0",
#   "matplotlib>=3.7.0",
#   "rich>=13.0.0",
# ]
# ///

"""Data Analysis Script Example.

This script demonstrates PEP 723 inline script metadata with uv.
It analyzes CSV data and creates visualizations.

Usage:
    # Make executable and run
    chmod +x data_analysis.py
    ./data_analysis.py data.csv

    # Or run directly with uv
    uv run data_analysis.py data.csv

    # With additional dependencies
    uv run --with seaborn data_analysis.py data.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# Minimum command-line arguments required: script name + CSV file path
MIN_REQUIRED_ARGS = 2


def analyze_data(csv_path: str) -> None:
    """Analyze CSV data and display summary statistics."""
    # Load data
    df = pd.read_csv(csv_path)

    console.print(f"[bold green]Analyzing {csv_path}[/bold green]")
    console.print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")

    # Display summary statistics in rich table
    table = Table(title="Summary Statistics")
    table.add_column("Column", style="cyan")
    table.add_column("Mean", style="magenta")
    table.add_column("Std", style="green")
    table.add_column("Min", style="yellow")
    table.add_column("Max", style="red")

    for col in df.select_dtypes(include=["number"]).columns:
        table.add_row(
            col, f"{df[col].mean():.2f}", f"{df[col].std():.2f}", f"{df[col].min():.2f}", f"{df[col].max():.2f}"
        )

    console.print(table)

    # Create visualization
    _fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Plot 1: Distribution of first numeric column
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 0:
        df[numeric_cols[0]].hist(ax=axes[0], bins=30)
        axes[0].set_title(f"Distribution of {numeric_cols[0]}")
        axes[0].set_xlabel(numeric_cols[0])
        axes[0].set_ylabel("Frequency")

    # Plot 2: Correlation heatmap
    if len(numeric_cols) > 1:
        corr = df.loc[:, numeric_cols].corr()
        im = axes[1].imshow(corr, cmap="coolwarm", aspect="auto")
        axes[1].set_xticks(range(len(numeric_cols)))
        axes[1].set_yticks(range(len(numeric_cols)))
        axes[1].set_xticklabels(numeric_cols, rotation=45)
        axes[1].set_yticklabels(numeric_cols)
        axes[1].set_title("Correlation Matrix")
        plt.colorbar(im, ax=axes[1])

    plt.tight_layout()
    output_path = Path(csv_path).stem + "_analysis.png"
    plt.savefig(output_path, dpi=150)
    console.print(f"\n[bold green]✓[/bold green] Saved visualization to {output_path}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < MIN_REQUIRED_ARGS:
        console.print("[bold red]Error:[/bold red] Please provide CSV file path")
        console.print("\nUsage: uv run data_analysis.py <csv_file>")
        sys.exit(1)

    csv_path = sys.argv[1]
    if not Path(csv_path).exists():
        console.print(f"[bold red]Error:[/bold red] File '{csv_path}' not found")
        sys.exit(1)

    try:
        analyze_data(csv_path)
    except pd.errors.ParserError as e:
        console.print(f"[bold red]CSV Parse Error:[/bold red] {e}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        console.print("[bold red]Error:[/bold red] CSV file is empty")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[bold red]Data Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
