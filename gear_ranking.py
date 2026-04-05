"""
gear_ranking.py
---------------
Rank shoes by running economy (vertical ratio) per pace zone,
using data from gear_analysis.csv.

Usage:
    # From another script
    from gear_ranking import top_shoes_by_zone, print_ranking

    ranking = top_shoes_by_zone(min_laps=10, top_n=3)
    print_ranking(ranking)

    # Or run directly
    python gear_ranking.py
    python gear_ranking.py --min-laps 15 --top-n 5
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CSV = Path(__file__).parent / "gear_analysis.csv"


@dataclass
class GearZoneEntry:
    gear: str
    zone: str
    laps: int
    total_distance_km: float
    avg_pace: str
    avg_stride_length_cm: float
    avg_vertical_osc_cm: float
    avg_vertical_ratio_pct: float


def load_csv(path: Path = DEFAULT_CSV) -> list[GearZoneEntry]:
    entries = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            entries.append(GearZoneEntry(
                gear=row["gear"],
                zone=row["zone"],
                laps=int(row["laps"]),
                total_distance_km=float(row["total_distance_km"]),
                avg_pace=row["avg_pace"],
                avg_stride_length_cm=float(row["avg_stride_length_cm"]),
                avg_vertical_osc_cm=float(row["avg_vertical_osc_cm"]),
                avg_vertical_ratio_pct=float(row["avg_vertical_ratio_pct"]),
            ))
    return entries


def top_shoes_by_zone(
    min_laps: int = 10,
    top_n: int = 3,
    csv_path: Path = DEFAULT_CSV,
) -> dict[str, list[GearZoneEntry]]:
    """
    Return top N shoes per pace zone ranked by vertical ratio (ascending).

    Args:
        min_laps:  Minimum laps required to include a shoe in rankings.
        top_n:     Number of top shoes to return per zone.
        csv_path:  Path to gear_analysis.csv.

    Returns:
        Dict mapping zone label → list of GearZoneEntry (best first).
    """
    entries = load_csv(csv_path)

    # Group by zone
    zones: dict[str, list[GearZoneEntry]] = {}
    for entry in entries:
        if entry.laps >= min_laps:
            zones.setdefault(entry.zone, []).append(entry)

    # Sort each zone by vertical ratio ascending and take top N
    ranked: dict[str, list[GearZoneEntry]] = {}
    for zone, zone_entries in zones.items():
        ranked[zone] = sorted(zone_entries, key=lambda e: e.avg_vertical_ratio_pct)[:top_n]

    # Return in zone order
    zone_order = [
        "Zone 1 (>5:15)",
        "Zone 2 (4:39–5:15)",
        "Zone 3 (4:17–4:39)",
        "Zone 4 (4:03–4:17)",
        "Zone 5 (3:44–4:03)",
        "Zone 6 (<3:44)",
    ]
    return {z: ranked[z] for z in zone_order if z in ranked}


def print_ranking(
    ranking: dict[str, list[GearZoneEntry]],
    min_laps: int | None = None,
) -> None:
    """Pretty-print the zone ranking table."""
    col = 24
    print()
    if min_laps is not None:
        print(f"  Minimum laps filter: {min_laps}  |  Ranked by vertical ratio (lower = better economy)")
    print()

    for zone, entries in ranking.items():
        if not entries:
            continue
        print(f"  {zone}")
        print(f"  {'#':<4}{'Shoe':<{col}}{'Vert Ratio':>12}{'Laps':>8}{'Avg Pace':>10}{'Stride (cm)':>13}{'Vert Osc (cm)':>15}")
        print("  " + "-" * (4 + col + 12 + 8 + 10 + 13 + 15))
        for i, e in enumerate(entries, 1):
            print(
                f"  {i:<4}{e.gear:<{col}}"
                f"{e.avg_vertical_ratio_pct:>11.2f}%"
                f"{e.laps:>8}"
                f"{e.avg_pace:>10}"
                f"{e.avg_stride_length_cm:>13.1f}"
                f"{e.avg_vertical_osc_cm:>15.2f}"
            )
        print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rank shoes by running economy per pace zone.")
    parser.add_argument("--min-laps", type=int, default=10, help="Minimum laps required (default: 10)")
    parser.add_argument("--top-n",    type=int, default=3,  help="Number of top shoes per zone (default: 3)")
    parser.add_argument("--csv",      type=Path, default=DEFAULT_CSV, help="Path to gear_analysis.csv")
    args = parser.parse_args()

    ranking = top_shoes_by_zone(min_laps=args.min_laps, top_n=args.top_n, csv_path=args.csv)
    print_ranking(ranking, min_laps=args.min_laps)
