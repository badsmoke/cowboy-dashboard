from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response


AUTH_HEADERS = {
    "client": "mock-client-token",
    "access-token": "mock-access-token",
    "uid": "mock-user@example.invalid",
}

MOCK_ME = {
    "id": 90001,
    "uuid": "00000000-0000-4000-8000-000000090001",
    "uid": "mock-user@example.invalid",
    "email": "mock-user@example.invalid",
    "nickname": "Demo Rider",
    "first_name": "Demo",
    "last_name": "Rider",
    "avatar_url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 96 96'%3E%3Crect width='96' height='96' rx='48' fill='%2369c3a5'/%3E%3Ctext x='48' y='57' text-anchor='middle' font-family='Arial' font-size='30' font-weight='700' fill='%2317211c'%3EDR%3C/text%3E%3C/svg%3E",
    "country_code": "DE",
    "total_distance": 2762.480006925687,
    "total_duration": 602097,
    "settings": {
        "distance_units": "kilometers",
        "temperature_units": "celsius",
        "weight_units": "kilograms",
        "privacy_diagnostics_and_analytics": True,
    },
    "bike": {
        "id": 90002,
        "nickname": "Demo Bike",
        "model": {"name": "Cowboy 3", "description": "Cowboy 3"},
        "sku": {
            "code": "DEMO-SKU-BLACK",
            "market": "EU",
            "color": "Black",
            "features": {
                "battery_autonomy": 60,
                "battery_leds": 5,
                "available_speeds": {"default": 28, "offroad": None},
                "displayed_speeds": {"default": 25, "offroad": None},
            },
        },
        "firmware_version": "v4.21.5",
        "seen_at": "2026-08-17T13:09:34.762+02:00",
        "autonomy": 61.14,
        "battery_state_of_charge": 90,
        "battery_state_of_charge_updated_at": "2026-08-17T13:09:34.762+02:00",
        "battery_inserted": True,
        "pcb_battery_state_of_charge": 91.0,
        "serial_number": "DEMO-SERIAL-0000",
        "total_distance": 2762.480006925687,
        "total_duration": 602097,
        "total_co2_saved": 345310,
        "position": {
            "latitude": 52.5208,
            "longitude": 13.4095,
            "source": "bike",
            "type": "stolen",
            "received_at": "2026-08-17T10:27:10.000+02:00",
        },
        "available_features": {
            "theft_alerts": "available",
            "auto_unlock": "available",
            "crash_detection": "available",
            "trip_analysis": "available",
            "strava": "available",
        },
        "last_ride_mode": "static_eu",
        "autonomies": [
            {"ride_mode": "adaptive_eu", "full_battery_range": 61.13, "calibrated": False},
            {"ride_mode": "static_eu", "full_battery_range": 61.13, "calibrated": True},
            {"ride_mode": "adaptive_eco_eu", "full_battery_range": 76.41, "calibrated": False},
        ],
        "settings": {
            "theft_alerts": True,
            "auto_unlock": True,
            "crash_detection": True,
            "led_brightness": 100,
            "manual_unlock": 10,
            "auto_lock": 5,
            "smart_lock": True,
            "max_speed": 28,
            "brake_light_sensitivity": 10,
            "default_ride_mode": "static_eu",
        },
    },
}

MOCK_PLACES = {
    "home": {
        "id": 1054648,
        "type": "home",
        "place_id": "mock-home-place",
        "name": "Demo Home",
        "user_label": "Demo Home",
        "address": "Demo City",
        "latitude": 52.5184,
        "longitude": 13.3763,
        "last_navigated_at": "2022-06-08T15:59:57.452+02:00",
        "full_address": "Demo City",
    },
    "work": {
        "id": 1054649,
        "type": "work",
        "place_id": "mock-work-place",
        "name": "Demo Work",
        "user_label": "Demo Work",
        "address": "Demo City",
        "latitude": 52.5159,
        "longitude": 13.4542,
        "last_navigated_at": "2022-05-02T15:27:15.770+02:00",
        "full_address": "Demo City",
    },
    "saved": [],
    "history": [
        {
            "id": 1054643,
            "type": "history",
            "place_id": "mock-history-place",
            "name": "Demo Stop",
            "user_label": None,
            "address": "Demo City",
            "latitude": 52.5269,
            "longitude": 13.3992,
            "last_navigated_at": "2022-03-31T19:36:28.689+02:00",
            "full_address": "Demo City",
        }
    ],
}

MOCK_TRIPS = [
    {
        "id": 42001,
        "uid": "mock-trip-42001",
        "title": "Morning ride",
        "started_at": "2026-08-17T08:10:00Z",
        "ended_at": "2026-08-17T08:31:00Z",
        "distance": 4.2,
        "unlocked_time": 1260,
        "moving_time": 1180,
        "average_speed": 12.8,
        "average_user_power": 92,
        "average_motor_power": 104,
        "has_dashboard_data": True,
    },
    {
        "id": 42002,
        "uid": "mock-trip-42002",
        "title": "Evening ride",
        "started_at": "2025-08-12T17:45:00Z",
        "ended_at": "2025-08-12T18:02:00Z",
        "distance": 3.1,
        "unlocked_time": 1020,
        "moving_time": 980,
        "average_speed": 11.4,
        "average_user_power": 88,
        "average_motor_power": 97,
        "has_dashboard_data": True,
    },
]

MOCK_CHARTS = {
    42001: {
        "positions": [[52.5208, 13.4095], [52.5194, 13.3928], [52.5184, 13.3763]],
        "durations": [0, 620, 1260],
        "distances": [0, 2100, 4200],
        "speeds": [0, 12.6, 13.2],
        "elevations": [116, 118, 120],
    },
    42002: {
        "positions": [[52.5184, 13.3763], [52.5227, 13.4171], [52.5159, 13.4542]],
        "durations": [0, 500, 1020],
        "distances": [0, 1550, 3100],
        "speeds": [0, 11.1, 11.8],
        "elevations": [120, 119, 116],
    },
}


def mock_trip_records() -> list[dict[str, Any]]:
    records = []
    for trip in MOCK_TRIPS:
        records.append({"trip": trip, "charts": MOCK_CHARTS.get(trip["id"])})
    return records


app = FastAPI(title="Mock Cowboy API", version="0.1.0")


def _require_auth(client: str | None, access_token: str | None, uid: str | None) -> None:
    if client != AUTH_HEADERS["client"] or access_token != AUTH_HEADERS["access-token"] or uid != AUTH_HEADERS["uid"]:
        raise HTTPException(status_code=401, detail={"errors": ["Unauthorized"]})


async def _trip_body(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}


@app.post("/auth/sign_in")
async def sign_in(request: Request, response: Response) -> dict[str, Any]:
    payload = await request.json()
    if not payload.get("email") or not payload.get("password"):
        raise HTTPException(status_code=401, detail={"errors": ["bad_credentials"]})
    for key, value in {**AUTH_HEADERS, "expiry": str(int(time.time()) + 60 * 60)}.items():
        response.headers[key] = value
    return {"data": {"id": MOCK_ME["id"], "uid": AUTH_HEADERS["uid"], "email": payload["email"]}}


@app.get("/users/me")
async def users_me(
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    return MOCK_ME


@app.get("/bikes/{bike_id}")
async def bike(
    bike_id: int,
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    if bike_id != MOCK_ME["bike"]["id"]:
        raise HTTPException(status_code=404, detail={"errors": ["Bike not found"]})
    return MOCK_ME["bike"]


@app.get("/users/me/places")
async def users_me_places(
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    return MOCK_PLACES


@app.post("/users/me/push_token")
async def push_token(
    request: Request,
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    payload = await request.json()
    return {"ok": True, "push_token": payload.get("push_token")}


@app.get("/trips")
async def trips(
    request: Request,
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    body = await _trip_body(request)
    page = int(body.get("page") or 1)
    from_text = body.get("from")
    to_text = body.get("to")

    filtered = MOCK_TRIPS
    if from_text and to_text:
        start = datetime.fromisoformat(from_text)
        end = datetime.fromisoformat(to_text)
        filtered = [
            trip
            for trip in MOCK_TRIPS
            if start <= datetime.fromisoformat(trip["started_at"].replace("Z", "+00:00")).replace(tzinfo=None) < end
        ]

    page_size = 1
    page_trips = filtered[(page - 1) * page_size : page * page_size]
    summaries: dict[str, dict[str, Any]] = {}
    for trip in page_trips:
        day = trip["started_at"][:10]
        summaries.setdefault(day, {"distance": 0, "duration": 0, "trips": []})
        summaries[day]["distance"] += trip.get("distance") or 0
        summaries[day]["duration"] += trip.get("unlocked_time") or 0
        summaries[day]["trips"].append(trip)

    return {"last_page": page * page_size >= len(filtered), "daily_summaries": summaries}


@app.get("/trips/{trip_id}")
async def trip(
    trip_id: int,
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    for item in MOCK_TRIPS:
        if item["id"] == trip_id:
            return item
    raise HTTPException(status_code=404, detail={"errors": ["Trip not found"]})


@app.get("/trips/{trip_id}/charts")
async def trip_charts(
    trip_id: int,
    client: str | None = Header(default=None),
    access_token: str | None = Header(default=None),
    uid: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(client, access_token, uid)
    if trip_id not in MOCK_CHARTS:
        raise HTTPException(status_code=404, detail={"errors": ["Charts not found"]})
    return MOCK_CHARTS[trip_id]
