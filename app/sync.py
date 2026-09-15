from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from .storage import TripStore, utc_now_iso

if TYPE_CHECKING:
    from .cowboy import CowboyClient


def sync_window(days: int, start: datetime | None = None) -> tuple[datetime, datetime]:
    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    oldest = end - timedelta(days=days)
    return (max(start, oldest) if start else oldest), end


async def list_trips_between(
    client: "CowboyClient",
    start_at: datetime,
    end_at: datetime,
    page_delay: float = 0.2,
) -> tuple[list[dict[str, Any]], int]:
    trips: list[dict[str, Any]] = []
    page = 1
    last_page = False

    while not last_page:
        data = await client.list_trips(start_at, end_at, page=page)
        daily_summaries = data.get("daily_summaries") or {}
        for day in daily_summaries.values():
            trips.extend(day.get("trips", []))
        last_page = bool(data.get("last_page", True))
        page += 1
        if not last_page and page_delay:
            await asyncio.sleep(page_delay)

    return trips, page - 1


async def list_all_trips(
    client: "CowboyClient",
    days: int,
    start: datetime | None = None,
    page_delay: float = 0.2,
) -> tuple[list[dict[str, Any]], int]:
    start_at, end_at = sync_window(days, start)
    return await list_trips_between(client, start_at, end_at, page_delay=page_delay)


async def sync_trips(
    client: "CowboyClient",
    store: TripStore,
    days: int = 400,
    overlap_days: int = 7,
    full: bool = False,
    workers: int = 4,
    chart_delay: float = 0.0,
) -> dict[str, Any]:
    store.ensure()
    desired_oldest, desired_end = sync_window(days)
    windows = []
    newest = None
    oldest = None
    if full:
        windows.append(("full", desired_oldest, desired_end))
    else:
        newest = store.newest_cached_start()
        oldest = store.oldest_cached_start()
        if newest is None:
            windows.append(("initial", desired_oldest, desired_end))
        else:
            recent_start = max(desired_oldest, newest - timedelta(days=overlap_days))
            windows.append(("recent", recent_start, desired_end))
            if oldest and desired_oldest < oldest:
                backfill_end = min(desired_end, oldest + timedelta(days=overlap_days))
                windows.append(("backfill", desired_oldest, backfill_end))

    trips_by_id: dict[Any, dict[str, Any]] = {}
    pages = 0
    listed_windows = []
    for label, start_at, end_at in windows:
        listed, listed_pages = await list_trips_between(client, start_at, end_at)
        pages += listed_pages
        listed_windows.append(
            {
                "label": label,
                "from": start_at.isoformat(),
                "to": end_at.isoformat(),
                "pages": listed_pages,
                "trips": len(listed),
            }
        )
        for trip in listed:
            trips_by_id[trip.get("id") or trip.get("uid") or id(trip)] = trip

    trips = list(trips_by_id.values())
    for trip in trips:
        store.save_trip_summary(trip)

    chart_candidates = [
        trip
        for trip in trips
        if trip.get("has_dashboard_data") and trip.get("id") is not None and not store.has_charts(trip["id"])
    ]

    state = {
        "started_at": utc_now_iso(),
        "finished_at": None,
        "days": days,
        "full": full,
        "overlap_days": overlap_days,
        "listed_pages": pages,
        "listed_trips": len(trips),
        "listed_windows": listed_windows,
        "new_chart_requests": len(chart_candidates),
        "charts_fetched": 0,
        "charts_failed": 0,
        "rate_limited": 0,
        "desired_oldest": desired_oldest.isoformat(),
        "incremental_from": windows[0][1].isoformat() if windows else None,
        "newest_cached_before": newest.isoformat() if newest else None,
        "oldest_cached_before": oldest.isoformat() if oldest else None,
    }

    semaphore = asyncio.Semaphore(max(1, workers))

    async def fetch_chart(trip: dict[str, Any]) -> None:
        async with semaphore:
            try:
                charts = await client.get_trip_charts(trip["id"])
                store.save_trip_charts(trip, charts)
                state["charts_fetched"] += 1
            except Exception as exc:
                state["charts_failed"] += 1
                if getattr(exc, "status_code", None) in (403, 429):
                    state["rate_limited"] += 1
            if chart_delay:
                await asyncio.sleep(chart_delay)

    if chart_candidates:
        await asyncio.gather(*(fetch_chart(trip) for trip in chart_candidates))

    state["finished_at"] = utc_now_iso()
    store.save_sync_state(state)
    return state
