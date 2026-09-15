from __future__ import annotations

import json
import os
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class TripStore:
    def __init__(self, root: str | os.PathLike[str] | None = None) -> None:
        self.root = Path(root or os.getenv("COWBOY_CACHE_DIR", "cowboy_cache"))
        self.trips_dir = self.root / "trips"
        self.api_cache_dir = self.root / "api"
        self.sync_state_file = self.root / "sync_state.json"

    def ensure(self) -> None:
        self.trips_dir.mkdir(parents=True, exist_ok=True)
        self.api_cache_dir.mkdir(parents=True, exist_ok=True)

    def clear(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)

    def trip_path(self, trip_id: int | str) -> Path:
        return self.trips_dir / f"{trip_id}.json"

    def load_trip_record(self, trip_id: int | str) -> dict[str, Any] | None:
        path = self.trip_path(trip_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save_trip_summary(self, trip: dict[str, Any]) -> None:
        self.ensure()
        trip_id = trip.get("id")
        if trip_id is None:
            return
        existing = self.load_trip_record(trip_id) or {}
        existing["trip"] = trip
        existing.setdefault("charts", None)
        existing["summary_cached_at"] = utc_now_iso()
        self.trip_path(trip_id).write_text(json.dumps(existing, separators=(",", ":")))

    def save_trip_charts(self, trip: dict[str, Any], charts: dict[str, Any]) -> None:
        self.ensure()
        trip_id = trip.get("id")
        if trip_id is None:
            return
        record = self.load_trip_record(trip_id) or {"trip": trip}
        record["trip"] = trip
        record["charts"] = charts
        record["charts_cached_at"] = utc_now_iso()
        self.trip_path(trip_id).write_text(json.dumps(record, separators=(",", ":")))

    def has_charts(self, trip_id: int | str) -> bool:
        record = self.load_trip_record(trip_id)
        return bool(record and record.get("charts"))

    def all_records(self) -> list[dict[str, Any]]:
        self.ensure()
        records = []
        for path in self.trips_dir.glob("*.json"):
            try:
                records.append(json.loads(path.read_text()))
            except (OSError, json.JSONDecodeError):
                continue
        return records

    def all_trips(self) -> list[dict[str, Any]]:
        trips = [record["trip"] for record in self.all_records() if isinstance(record.get("trip"), dict)]
        return sorted(trips, key=lambda trip: trip.get("started_at") or "", reverse=True)

    def newest_cached_start(self) -> datetime | None:
        return self.cached_start_boundary(newest=True)

    def oldest_cached_start(self) -> datetime | None:
        return self.cached_start_boundary(newest=False)

    def cached_start_boundary(self, newest: bool) -> datetime | None:
        boundary = None
        self.ensure()
        for path in self.trips_dir.glob("*.json"):
            try:
                with path.open("rb") as handle:
                    head = handle.read(4096).decode("utf-8", "replace")
            except OSError:
                continue
            match = re.search(r'"started_at"\s*:\s*"([^"]+)"', head)
            if not match:
                continue
            try:
                started = parse_datetime(match.group(1))
            except ValueError:
                continue
            if boundary is None or (started > boundary if newest else started < boundary):
                boundary = started
        return boundary

    def save_sync_state(self, state: dict[str, Any]) -> None:
        self.ensure()
        self.sync_state_file.write_text(json.dumps(state, indent=2, sort_keys=True))

    def load_sync_state(self) -> dict[str, Any]:
        if not self.sync_state_file.exists():
            return {}
        try:
            return json.loads(self.sync_state_file.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def load_api_cache(self, name: str, max_age_s: int) -> dict[str, Any] | None:
        self.ensure()
        path = self.api_cache_dir / f"{name}.json"
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text())
            cached_at = parse_datetime(payload.get("cached_at", ""))
        except (OSError, json.JSONDecodeError, ValueError):
            return None
        age = (datetime.now().astimezone().replace(tzinfo=None) - cached_at).total_seconds()
        if age > max_age_s:
            return None
        return payload.get("data")

    def save_api_cache(self, name: str, data: dict[str, Any]) -> None:
        self.ensure()
        path = self.api_cache_dir / f"{name}.json"
        payload = {"cached_at": utc_now_iso(), "data": data}
        path.write_text(json.dumps(payload, separators=(",", ":")))

    def geojson(self) -> dict[str, Any]:
        features = []
        dropped = 0
        for record in self.all_records():
            trip = record.get("trip") or {}
            charts = record.get("charts") or {}
            coords = [
                [point[1], point[0]]
                for point in charts.get("positions") or []
                if point and len(point) == 2 and point[0] is not None and point[1] is not None
            ]
            if len(coords) < 2:
                if charts:
                    dropped += 1
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "id": trip.get("id"),
                        "uid": trip.get("uid"),
                        "title": trip.get("title"),
                        "started_at": trip.get("started_at"),
                        "distance_km": trip.get("distance"),
                        "duration_s": trip.get("unlocked_time") or trip.get("moving_time"),
                    },
                }
            )
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {"dropped": dropped},
        }

    def overview(self) -> dict[str, Any]:
        trips = self.all_trips()
        records = self.all_records()
        distances = [trip.get("distance") or 0 for trip in trips]
        durations = [trip.get("unlocked_time") or trip.get("moving_time") or 0 for trip in trips]
        route_count = sum(1 for record in records if has_usable_route(record))
        return {
            "trip_count": len(trips),
            "route_count": route_count,
            "total_distance_km": round(sum(distances), 2),
            "total_duration_s": int(sum(durations)),
            "first_trip_at": trips[-1].get("started_at") if trips else None,
            "last_trip_at": trips[0].get("started_at") if trips else None,
            "sync": self.load_sync_state(),
        }


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def has_usable_route(record: dict[str, Any]) -> bool:
    charts = record.get("charts") or {}
    positions = charts.get("positions") or []
    usable_points = 0
    for point in positions:
        if isinstance(point, (list, tuple)) and len(point) == 2 and point[0] is not None and point[1] is not None:
            usable_points += 1
        if usable_points >= 2:
            return True
    return False
