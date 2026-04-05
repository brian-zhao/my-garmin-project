"""
Analyse running dynamics (stride length, vertical oscillation, vertical ratio)
by pace zone across all activities for a given gear UUID, or all gear for
cross-gear comparison.

Pace zones (min:sec per km):
  Zone 1  — slower than 5:15
  Zone 2  — 4:39 – 5:15
  Zone 3  — 4:17 – 4:39
  Zone 4  — 4:03 – 4:17
  Zone 5  — 3:44 – 4:03
  Zone 6  — faster than 3:44
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from garmin_auth import garmin_login
from gear_enum import Gear

if TYPE_CHECKING:
    from garminconnect import Garmin


# ---------------------------------------------------------------------------
# Pace zone definitions
# ---------------------------------------------------------------------------

def _pace_to_speed(minutes: int, seconds: int) -> float:
    """Convert min:sec per km to metres per second."""
    return 1000 / (minutes * 60 + seconds)


class PaceZone(Enum):
    ZONE_1 = "Zone 1 (>5:15)"
    ZONE_2 = "Zone 2 (4:39–5:15)"
    ZONE_3 = "Zone 3 (4:17–4:39)"
    ZONE_4 = "Zone 4 (4:03–4:17)"
    ZONE_5 = "Zone 5 (3:44–4:03)"
    ZONE_6 = "Zone 6 (<3:44)"


# Speed boundaries in m/s (upper bound for each zone, ascending)
_ZONE_BOUNDARIES: list[tuple[float, PaceZone]] = [
    (_pace_to_speed(5, 15), PaceZone.ZONE_1),   # < 3.175 m/s
    (_pace_to_speed(4, 39), PaceZone.ZONE_2),   # 3.175 – 3.584
    (_pace_to_speed(4, 17), PaceZone.ZONE_3),   # 3.584 – 3.891
    (_pace_to_speed(4,  3), PaceZone.ZONE_4),   # 3.891 – 4.115
    (_pace_to_speed(3, 44), PaceZone.ZONE_5),   # 4.115 – 4.464
]


def classify_pace(speed_ms: float) -> PaceZone:
    for boundary, zone in _ZONE_BOUNDARIES:
        if speed_ms <= boundary:
            return zone
    return PaceZone.ZONE_6


def speed_to_pace(speed_ms: float) -> str:
    """Format m/s as mm:ss /km string."""
    if speed_ms <= 0:
        return "--:--"
    sec_per_km = 1000 / speed_ms
    mins = int(sec_per_km // 60)
    secs = int(sec_per_km % 60)
    return f"{mins}:{secs:02d}"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LapSample:
    activity_id: int
    activity_name: str
    lap_index: int
    pace_str: str
    speed_ms: float
    stride_length_cm: float
    vertical_oscillation_cm: float
    vertical_ratio_pct: float
    distance_m: float
    duration_s: float


@dataclass
class ZoneStats:
    zone: PaceZone
    samples: list[LapSample] = field(default_factory=list)

    def add(self, sample: LapSample) -> None:
        self.samples.append(sample)

    def _avg(self, values: list[float]) -> float:
        return statistics.mean(values) if values else 0.0

    def _std(self, values: list[float]) -> float:
        return statistics.stdev(values) if len(values) > 1 else 0.0

    def summary(self) -> dict:
        if not self.samples:
            return {}

        strides   = [s.stride_length_cm for s in self.samples]
        vo        = [s.vertical_oscillation_cm for s in self.samples]
        vr        = [s.vertical_ratio_pct for s in self.samples]
        speeds    = [s.speed_ms for s in self.samples]
        total_dist = sum(s.distance_m for s in self.samples)

        return {
            "zone":                    self.zone.value,
            "lap_count":               len(self.samples),
            "total_distance_km":       round(total_dist / 1000, 2),
            "avg_pace":                speed_to_pace(self._avg(speeds)),
            "avg_stride_length_cm":    round(self._avg(strides), 1),
            "std_stride_length_cm":    round(self._std(strides), 1),
            "avg_vertical_osc_cm":     round(self._avg(vo), 2),
            "std_vertical_osc_cm":     round(self._std(vo), 2),
            "avg_vertical_ratio_pct":  round(self._avg(vr), 2),
            "std_vertical_ratio_pct":  round(self._std(vr), 2),
        }


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

_MIN_LAP_DISTANCE_M = 200   # ignore very short laps (standing, transitions)
_SKIP_INTENSITY = {"REST"}  # skip rest laps


def fetch_laps_for_gear(gear: Gear, client: "Garmin") -> tuple[list[LapSample], list[str]]:
    """Fetch all laps from all activities for the given gear."""
    activities = client.get_gear_activities(gear.value)

    samples: list[LapSample] = []
    warnings: list[str] = []

    for activity in activities:
        activity_id   = activity["activityId"]
        activity_name = activity.get("activityName", str(activity_id))

        try:
            splits = client.get_activity_splits(activity_id)
        except Exception as exc:
            warnings.append(f"Could not fetch splits for {activity_id}: {exc}")
            continue

        for lap in splits.get("lapDTOs", []):
            intensity = lap.get("intensityType", "")
            if intensity in _SKIP_INTENSITY:
                continue

            distance = lap.get("distance") or 0
            if distance < _MIN_LAP_DISTANCE_M:
                continue

            speed            = lap.get("averageSpeed") or 0
            stride_length    = lap.get("strideLength")
            vertical_osc     = lap.get("verticalOscillation")
            vertical_ratio   = lap.get("verticalRatio")

            # Skip laps missing running dynamics data
            if None in (stride_length, vertical_osc, vertical_ratio) or speed <= 0:
                continue

            samples.append(LapSample(
                activity_id=activity_id,
                activity_name=activity_name,
                lap_index=lap.get("lapIndex", 0),
                pace_str=speed_to_pace(speed),
                speed_ms=speed,
                stride_length_cm=stride_length,
                vertical_oscillation_cm=vertical_osc,
                vertical_ratio_pct=vertical_ratio,
                distance_m=distance,
                duration_s=lap.get("duration") or 0,
            ))

    return samples, warnings


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyse(gear: Gear, client: "Garmin") -> dict[PaceZone, ZoneStats]:
    samples, warnings = fetch_laps_for_gear(gear, client)

    zone_stats: dict[PaceZone, ZoneStats] = {z: ZoneStats(z) for z in PaceZone}
    for sample in samples:
        zone = classify_pace(sample.speed_ms)
        zone_stats[zone].add(sample)

    for w in warnings:
        print(f"WARNING: {w}")

    return zone_stats


def analyse_all_gear() -> dict[Gear, dict[PaceZone, ZoneStats]]:
    """Fetch and analyse every gear item, reusing a single login."""
    client = garmin_login()
    results: dict[Gear, dict[PaceZone, ZoneStats]] = {}

    for gear in Gear:
        gear_label = gear.name.replace("_", " ").title()
        print(f"  Fetching {gear_label}...")
        zone_stats = analyse(gear, client)
        total_laps = sum(len(zs.samples) for zs in zone_stats.values())
        if total_laps > 0:
            results[gear] = zone_stats

    return results


# ---------------------------------------------------------------------------
# Pretty-print report
# ---------------------------------------------------------------------------

def print_report(zone_stats: dict[PaceZone, ZoneStats]) -> None:
    print("\n" + "=" * 70)
    print("  RUNNING DYNAMICS BY PACE ZONE")
    print("=" * 70)

    for zone in PaceZone:
        stats = zone_stats[zone]
        summary = stats.summary()
        if not summary:
            continue

        print(f"\n{summary['zone']}")
        print(f"  Laps              : {summary['lap_count']}  ({summary['total_distance_km']} km)")
        print(f"  Avg pace          : {summary['avg_pace']} /km")
        print(f"  Stride length     : {summary['avg_stride_length_cm']} cm  (±{summary['std_stride_length_cm']})")
        print(f"  Vertical osc.     : {summary['avg_vertical_osc_cm']} cm   (±{summary['std_vertical_osc_cm']})")
        print(f"  Vertical ratio    : {summary['avg_vertical_ratio_pct']} %  (±{summary['std_vertical_ratio_pct']})  ← running economy")

    print("\n" + "=" * 70)
    print("  Lower vertical ratio = better running economy")
    print("=" * 70 + "\n")


# ---------------------------------------------------------------------------
# Cross-gear comparison report
# ---------------------------------------------------------------------------

_METRICS = [
    ("avg_stride_length_cm",   "Stride (cm)  "),
    ("avg_vertical_osc_cm",    "Vert osc (cm)"),
    ("avg_vertical_ratio_pct", "Vert ratio % "),
]


def print_comparison_report(all_results: dict[Gear, dict[PaceZone, ZoneStats]]) -> None:
    gear_labels = {
        gear: gear.name.replace("_", " ").title()
        for gear in all_results
    }
    col_w = 16

    for zone in PaceZone:
        # Collect summaries for this zone across all gear that have data here
        zone_data: dict[Gear, dict] = {}
        for gear, zone_stats in all_results.items():
            summary = zone_stats[zone].summary()
            if summary:
                zone_data[gear] = summary

        if not zone_data:
            continue

        print("\n" + "=" * (14 + col_w * len(zone_data)))
        print(f"  {zone.value}")
        print("=" * (14 + col_w * len(zone_data)))

        # Header row
        header = f"{'':14}" + "".join(f"{gear_labels[g]:>{col_w}}" for g in zone_data)
        print(header)
        print(f"{'Avg pace':14}" + "".join(f"{zone_data[g]['avg_pace']:>{col_w}}" for g in zone_data))
        print(f"{'Laps':14}" + "".join(f"{zone_data[g]['lap_count']:>{col_w}}" for g in zone_data))

        for key, label in _METRICS:
            row = f"{label:14}" + "".join(f"{zone_data[g][key]:>{col_w}}" for g in zone_data)
            print(row)

    print("\n" + "-" * 60)
    print("  Lower vertical ratio = better running economy")
    print("-" * 60 + "\n")


# ---------------------------------------------------------------------------
# Save to CSV
# ---------------------------------------------------------------------------

def save_csv(all_results: dict[Gear, dict[PaceZone, ZoneStats]], path: str = "gear_analysis.csv") -> None:
    import csv

    rows = []
    for gear, zone_stats in all_results.items():
        gear_label = gear.name.replace("_", " ").title()
        for zone in PaceZone:
            summary = zone_stats[zone].summary()
            if not summary:
                continue
            rows.append({
                "gear":                   gear_label,
                "zone":                   zone.value,
                "laps":                   summary["lap_count"],
                "total_distance_km":      summary["total_distance_km"],
                "avg_pace":               summary["avg_pace"],
                "avg_stride_length_cm":   summary["avg_stride_length_cm"],
                "std_stride_length_cm":   summary["std_stride_length_cm"],
                "avg_vertical_osc_cm":    summary["avg_vertical_osc_cm"],
                "std_vertical_osc_cm":    summary["std_vertical_osc_cm"],
                "avg_vertical_ratio_pct": summary["avg_vertical_ratio_pct"],
                "std_vertical_ratio_pct": summary["std_vertical_ratio_pct"],
            })

    fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved {len(rows)} rows to {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Fetching data for all gear...\n")
    all_results = analyse_all_gear()
    print_comparison_report(all_results)
    save_csv(all_results)
