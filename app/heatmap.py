from __future__ import annotations

import math
from collections import Counter
from datetime import datetime
from typing import Any


def road_frequency_geojson(
    records: list[dict[str, Any]],
    grid_m: float = 10.0,
    date_prefix: str = "",
    date_from: str = "",
    date_to: str = "",
) -> dict[str, Any]:
    tracks = []
    matching_trips = 0
    cached_routes = 0
    dropped_routes = 0
    for record in records:
        trip = record.get("trip") or {}
        started_at = trip.get("started_at") or ""
        if not matches_date_filter(started_at, date_prefix, date_from, date_to):
            continue
        matching_trips += 1
        charts = record.get("charts") or {}
        if charts:
            cached_routes += 1
        coords = [
            [point[1], point[0]]
            for point in charts.get("positions") or []
            if point and len(point) == 2 and point[0] is not None and point[1] is not None
        ]
        if len(coords) >= 2:
            tracks.append({"trip": trip, "coords": coords})
        elif charts:
            dropped_routes += 1

    if not tracks:
        return empty_collection(
            grid_m=grid_m,
            date_prefix=date_prefix,
            date_from=date_from,
            date_to=date_to,
            matching_trips=matching_trips,
            cached_routes=cached_routes,
            dropped_routes=dropped_routes,
        )

    lats = [coord[1] for track in tracks for coord in track["coords"]]
    mean_lat = sum(lats) / len(lats)
    metres_per_lat = 111_320.0
    metres_per_lng = 111_320.0 * max(math.cos(math.radians(mean_lat)), 1e-6)
    dlat = grid_m / metres_per_lat
    dlng = grid_m / metres_per_lng

    counts: Counter[tuple[tuple[int, int], tuple[int, int]]] = Counter()
    trip_transitions = []

    for track in tracks:
        coords = track["coords"]
        cells = [(round(coord[1] / dlat), round(coord[0] / dlng)) for coord in coords]
        transitions = []
        seen_in_trip = set()
        prev = cells[0]
        entered = 0
        for idx in range(1, len(cells)):
            current = cells[idx]
            if current == prev:
                continue
            key = (prev, current) if prev <= current else (current, prev)
            transitions.append((key, entered, idx))
            seen_in_trip.add(key)
            prev = current
            entered = idx
        counts.update(seen_in_trip)
        trip_transitions.append((coords, transitions))

    max_count = max(counts.values(), default=0)
    grouped: dict[int, list[list[list[float]]]] = {}
    claimed = set()

    def emit(coords: list[list[float]], start: int, end: int, pairs: int, count: int) -> None:
        segment = simplify_segment(coords[start : end + 1], max_points=max(2, pairs * 3))
        if len(segment) >= 2:
            grouped.setdefault(count, []).append(segment)

    for coords, transitions in trip_transitions:
        start = end = run_count = None
        run_pairs = 0
        for key, entered, idx in transitions:
            fresh = key not in claimed
            count = counts[key]
            if fresh and start is not None and entered == end and count == run_count:
                end = idx
                run_pairs += 1
            else:
                if start is not None:
                    emit(coords, start, end, run_pairs, run_count)
                if fresh:
                    start = entered
                    end = idx
                    run_count = count
                    run_pairs = 1
                else:
                    start = end = run_count = None
                    run_pairs = 0
            claimed.add(key)
        if start is not None:
            emit(coords, start, end, run_pairs, run_count)

    features = []
    for count, lines in grouped.items():
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "MultiLineString", "coordinates": lines},
                "properties": {
                    "count": count,
                    "weight": count / max_count if max_count else 0,
                },
            }
        )

    features.sort(key=lambda feature: feature["properties"]["count"])
    return {
        "type": "FeatureCollection",
            "features": features,
        "properties": {
            "grid_m": grid_m,
            "date_prefix": date_prefix,
            "date_from": date_from,
            "date_to": date_to,
            "trips": len(tracks),
            "routes": len(tracks),
            "matching_trips": matching_trips,
            "cached_routes": cached_routes,
            "dropped_routes": dropped_routes,
            "stretches": len(counts),
            "paths": sum(len(lines) for lines in grouped.values()),
            "shapes": len(features),
            "max_count": max_count,
        },
    }


def matches_date_filter(started_at: str, date_prefix: str = "", date_from: str = "", date_to: str = "") -> bool:
    if not started_at:
        return not date_prefix and not date_from and not date_to
    if date_prefix and not started_at.startswith(date_prefix):
        return False
    if not date_from and not date_to:
        return True
    try:
        day = datetime.fromisoformat(started_at[:10]).date()
    except ValueError:
        return False
    if date_from and day < datetime.fromisoformat(date_from).date():
        return False
    if date_to and day > datetime.fromisoformat(date_to).date():
        return False
    return True


def simplify_segment(coords: list[list[float]], max_points: int = 12) -> list[list[float]]:
    if len(coords) <= max_points:
        return coords
    step = (len(coords) - 1) / (max_points - 1)
    return [coords[round(idx * step)] for idx in range(max_points)]


def empty_collection(
    grid_m: float,
    date_prefix: str,
    date_from: str = "",
    date_to: str = "",
    matching_trips: int = 0,
    cached_routes: int = 0,
    dropped_routes: int = 0,
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "grid_m": grid_m,
            "date_prefix": date_prefix,
            "date_from": date_from,
            "date_to": date_to,
            "trips": 0,
            "routes": 0,
            "matching_trips": matching_trips,
            "cached_routes": cached_routes,
            "dropped_routes": dropped_routes,
            "stretches": 0,
            "paths": 0,
            "shapes": 0,
            "max_count": 0,
        },
    }
