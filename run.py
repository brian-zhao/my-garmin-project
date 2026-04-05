"""
run.py — Main entry point for Garmin Running Analytics.

    python run.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-load .env before anything else
# ---------------------------------------------------------------------------

ENV_FILE = Path(__file__).parent / ".env"


def _load_env() -> None:
    if not ENV_FILE.exists():
        print("\n  No .env file found. Please run setup first:\n")
        print("      python setup.py\n")
        sys.exit(1)
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


_load_env()

# ---------------------------------------------------------------------------
# Imports (after env is loaded)
# ---------------------------------------------------------------------------

from gear_enum import Gear
from gear_ranking import top_shoes_by_zone, print_ranking


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    print("\n" + "=" * 52)
    print(f"  {title}")
    print("=" * 52)


def _prompt_int(prompt: str, default: int) -> int:
    raw = input(f"  {prompt} [{default}]: ").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        print(f"  Invalid input — using {default}")
        return default


def _prompt_date(prompt: str) -> datetime | None:
    raw = input(f"  {prompt} (YYYY-MM-DD, or press Enter to skip): ").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        print("  Invalid date format — skipping date filter")
        return None


def _all_shoe_names() -> list[str]:
    return sorted({g.name.replace("_", " ").title() for g in Gear})


def _pick_shoes() -> list[Gear]:
    names = _all_shoe_names()
    print("\n  Available shoes:")
    for i, name in enumerate(names, 1):
        print(f"    {i:>2}. {name}")
    raw = input("\n  Enter numbers separated by commas (e.g. 1,3,5): ").strip()
    selected: list[Gear] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            gear_name = names[idx].upper().replace(" ", "_")
            selected.append(Gear[gear_name])
        except (ValueError, IndexError, KeyError):
            print(f"  Skipping invalid selection: {part.strip()}")
    return selected


# ---------------------------------------------------------------------------
# Menu actions
# ---------------------------------------------------------------------------

def action_refresh_data() -> None:
    _header("Refresh Data from Garmin")
    print("\n  This fetches all laps for every gear item and rebuilds")
    print("  gear_analysis.csv. It may take 1–3 minutes.\n")
    confirm = input("  Continue? (Y/n): ").strip().lower()
    if confirm == "n":
        return

    from interval_analysis import analyse_all_gear, save_csv, print_comparison_report

    print()
    all_results = analyse_all_gear()
    print_comparison_report(all_results)
    save_csv(all_results)
    print("\n  ✓  gear_analysis.csv updated.")


def action_top_shoes() -> None:
    _header("Top Shoes by Pace Zone")
    min_laps = _prompt_int("Minimum laps per zone", 10)
    top_n    = _prompt_int("Number of top shoes to show", 3)

    csv_path = Path(__file__).parent / "gear_analysis.csv"
    if not csv_path.exists():
        print("\n  No data found. Please run option 1 (Refresh Data) first.\n")
        return

    ranking = top_shoes_by_zone(min_laps=min_laps, top_n=top_n)
    print_ranking(ranking, min_laps=min_laps)


def action_compare_shoes() -> None:
    _header("Compare Specific Shoes")

    csv_path = Path(__file__).parent / "gear_analysis.csv"
    has_csv  = csv_path.exists()

    print("\n  Data source:")
    print("    1. Use saved data (fast, from gear_analysis.csv)")
    print("    2. Fetch live from Garmin (supports date filter)")
    source = input("\n  Choose [1]: ").strip() or "1"

    if source == "1":
        if not has_csv:
            print("\n  No saved data found. Please run option 1 (Refresh Data) first.\n")
            return
        _compare_from_csv()
    else:
        _compare_live()


def _compare_from_csv() -> None:
    import csv
    from interval_analysis import PaceZone

    csv_path = Path(__file__).parent / "gear_analysis.csv"
    selected = _pick_shoes()
    if not selected:
        print("  No shoes selected.")
        return

    selected_labels = {g.name.replace("_", " ").title() for g in selected}

    with open(csv_path, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["gear"] in selected_labels]

    zone_order = [z.value for z in PaceZone]
    _print_shoe_table(rows, zone_order, selected_labels)


def _compare_live() -> None:
    from interval_analysis import (
        classify_pace, speed_to_pace, PaceZone,
        _MIN_LAP_DISTANCE_M, _SKIP_INTENSITY,
    )
    import statistics
    from garmin_auth import garmin_login

    selected = _pick_shoes()
    if not selected:
        print("  No shoes selected.")
        return

    cutoff = _prompt_date("Show activities after")

    print("\n  Fetching data from Garmin...\n")
    client = garmin_login()

    rows = []
    for gear in selected:
        gear_label = gear.name.replace("_", " ").title()
        activities  = client.get_gear_activities(gear.value)

        if cutoff:
            activities = [
                a for a in activities
                if datetime.strptime(a["startTimeLocal"][:10], "%Y-%m-%d") >= cutoff
            ]

        zone_data: dict[PaceZone, list] = {z: [] for z in PaceZone}

        for activity in activities:
            try:
                splits = client.get_activity_splits(activity["activityId"])
            except Exception:
                continue
            for lap in splits.get("lapDTOs", []):
                if lap.get("intensityType") in _SKIP_INTENSITY:
                    continue
                if (lap.get("distance") or 0) < _MIN_LAP_DISTANCE_M:
                    continue
                speed = lap.get("averageSpeed") or 0
                sl    = lap.get("strideLength")
                vo    = lap.get("verticalOscillation")
                vr    = lap.get("verticalRatio")
                if None in (sl, vo, vr) or speed <= 0:
                    continue
                zone_data[classify_pace(speed)].append((speed, sl, vo, vr, lap.get("distance", 0)))

        for zone, samples in zone_data.items():
            if not samples:
                continue
            speeds, strides, vos, vrs, dists = zip(*samples)
            rows.append({
                "gear":                   gear_label,
                "zone":                   zone.value,
                "laps":                   str(len(samples)),
                "avg_pace":               speed_to_pace(statistics.mean(speeds)),
                "avg_stride_length_cm":   str(round(statistics.mean(strides), 1)),
                "avg_vertical_osc_cm":    str(round(statistics.mean(vos), 2)),
                "avg_vertical_ratio_pct": str(round(statistics.mean(vrs), 2)),
                "total_distance_km":      str(round(sum(dists) / 1000, 1)),
            })

    selected_labels = {g.name.replace("_", " ").title() for g in selected}
    zone_order = [z.value for z in PaceZone]
    _print_shoe_table(rows, zone_order, selected_labels)


def _print_shoe_table(
    rows: list[dict],
    zone_order: list[str],
    selected_labels: set[str],
) -> None:
    print()
    for zone in zone_order:
        zone_rows = sorted(
            [r for r in rows if r["zone"] == zone],
            key=lambda r: float(r["avg_vertical_ratio_pct"]),
        )
        if not zone_rows:
            continue
        print(f"  {zone}")
        print(f"  {'Shoe':<24} {'VR%':>6} {'Laps':>5} {'Pace':>7} {'Stride':>8} {'Vert Osc':>10} {'Dist km':>8}")
        print("  " + "-" * 72)
        for r in zone_rows:
            print(
                f"  {r['gear']:<24}"
                f" {float(r['avg_vertical_ratio_pct']):>6.2f}"
                f" {int(r['laps']):>5}"
                f" {r['avg_pace']:>7}"
                f" {float(r['avg_stride_length_cm']):>8.1f}"
                f" {float(r['avg_vertical_osc_cm']):>10.2f}"
                f" {float(r['total_distance_km']):>8.1f}"
            )
        print()

    missing = selected_labels - {r["gear"] for r in rows}
    if missing:
        print(f"  (No data found for: {', '.join(sorted(missing))})\n")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = """
  1.  Refresh data from Garmin
  2.  Top shoes by pace zone
  3.  Compare specific shoes
  0.  Exit
"""


def main() -> None:
    print("\n" + "=" * 52)
    print("  🏃 Garmin Running Analytics")
    print("=" * 52)

    while True:
        print(MENU)
        choice = input("  Choose an option: ").strip()

        if choice == "1":
            action_refresh_data()
        elif choice == "2":
            action_top_shoes()
        elif choice == "3":
            action_compare_shoes()
        elif choice == "0":
            print("\n  Goodbye!\n")
            break
        else:
            print("  Invalid choice — please enter 0, 1, 2, or 3.")


if __name__ == "__main__":
    main()
