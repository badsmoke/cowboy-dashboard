from __future__ import annotations

import hashlib
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

import httpx
from fastapi import Body, Cookie, Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from .cowboy import CowboyAPIError, CowboyClient
from .heatmap import road_frequency_geojson
from .storage import TripStore, parse_datetime, utc_now_iso
from .sync import sync_trips


clients: dict[str, CowboyClient] = {}
sessions: dict[str, CowboyClient] = {}
store = TripStore()
PROFILE_CACHE_SECONDS = 10 * 60
MOCK_SERVER_ENV = "COWBOY_MOCK_SERVER"


def mock_server_enabled() -> bool:
    value = os.getenv(MOCK_SERVER_ENV, "false").strip().lower()
    return value in {"1", "true", "yes", "on"}


def create_cowboy_client(email: str, password: str) -> CowboyClient:
    if not mock_server_enabled():
        return CowboyClient(email, password)

    from .mock_cowboy import app as mock_cowboy_app

    return CowboyClient(
        email,
        password,
        base_url="http://mock-cowboy",
        transport=httpx.ASGITransport(app=mock_cowboy_app),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    discard_mock_store_if_needed()
    seed_mock_store_if_needed()
    yield
    seen = set()
    for client in [*clients.values(), *sessions.values()]:
        if id(client) in seen:
            continue
        seen.add(id(client))
        await client.close()


app = FastAPI(
    title="Cowboy API",
    description="Small Python Docker server for selected Cowboy Bike API calls.",
    version="0.1.0",
    lifespan=lifespan,
)


def seed_mock_store_if_needed() -> None:
    if not mock_server_enabled():
        return

    from .mock_cowboy import MOCK_ME, mock_trip_records

    state = store.load_sync_state()
    records = []
    if not store.all_trips() or state.get("mock") is True:
        store.save_api_cache("me-mock-user@example.invalid", MOCK_ME)
        if MOCK_ME.get("bike", {}).get("id"):
            store.save_api_cache(f"bike-{MOCK_ME['bike']['id']}", MOCK_ME["bike"])
        records = mock_trip_records()
        for record in records:
            trip = record.get("trip") or {}
            charts = record.get("charts") or {}
            if charts:
                store.save_trip_charts(trip, charts)
            else:
                store.save_trip_summary(trip)

    if state and not state.get("mock"):
        return
    if _valid_sync_timestamp(state.get("started_at")) and _valid_sync_timestamp(state.get("finished_at")):
        return

    all_records = records or store.all_records()
    save_mock_sync_state(all_records)


def discard_mock_store_if_needed() -> None:
    if mock_server_enabled():
        return
    if store.load_sync_state().get("mock") is True:
        store.clear()


def save_mock_sync_state(records: list[dict]) -> None:
    synced_at = utc_now_iso()
    store.save_sync_state(
        {
            "started_at": synced_at,
            "finished_at": synced_at,
            "mock": True,
            "listed_trips": len(records),
            "charts_fetched": len([record for record in records if record.get("charts")]),
        }
    )


def _valid_sync_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parse_datetime(value)
    except ValueError:
        return False
    return True


class PushTokenRequest(BaseModel):
    push_token: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=1)


class SyncRequest(BaseModel):
    days: int = Field(default=400, ge=1, le=5000)
    overlap_days: int = Field(default=7, ge=0, le=90)
    full: bool = False
    workers: int = Field(default=4, ge=1, le=16)
    chart_delay: float = Field(default=0.0, ge=0, le=10)


def client_key(email: str, password: str) -> str:
    digest = hashlib.sha256(f"{email}\0{password}".encode("utf-8")).hexdigest()
    return digest


async def get_cowboy_client(
    cowboy_session: Annotated[str | None, Cookie()] = None,
    x_cowboy_email: Annotated[str | None, Header()] = None,
    x_cowboy_password: Annotated[str | None, Header()] = None,
) -> CowboyClient:
    if cowboy_session and cowboy_session in sessions:
        return sessions[cowboy_session]

    email = x_cowboy_email or os.getenv("COWBOY_EMAIL")
    password = x_cowboy_password or os.getenv("COWBOY_PASSWORD")
    if not email or not password:
        raise HTTPException(status_code=401, detail="Login required.")
    key = client_key(email, password)
    if key not in clients:
        clients[key] = create_cowboy_client(email, password)
    return clients[key]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "cowboy_mock_server": str(mock_server_enabled()).lower()}


@app.post("/api/auth/login")
async def login(body: Annotated[LoginRequest, Body()], response: Response) -> dict:
    client = create_cowboy_client(body.email, body.password)
    try:
        await client.login()
    except CowboyAPIError as exc:
        await client.close()
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc

    discard_mock_store_if_needed()
    token = secrets.token_urlsafe(32)
    sessions[token] = client
    response.set_cookie(
        "cowboy_session",
        token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=60 * 60 * 24 * 30,
    )
    return {"authenticated": True, "uid": client.session.uid, "expires_at": client.session.expiry}


@app.post("/api/auth/logout")
async def logout(
    response: Response,
    cowboy_session: Annotated[str | None, Cookie()] = None,
) -> dict[str, bool]:
    if cowboy_session and cowboy_session in sessions:
        client = sessions.pop(cowboy_session)
        await client.close()
    response.delete_cookie("cowboy_session")
    return {"authenticated": False}


@app.get("/api/session")
async def session(cowboy_session: Annotated[str | None, Cookie()] = None) -> dict:
    client = sessions.get(cowboy_session or "")
    if client is None:
        return {"authenticated": False}
    return {"authenticated": True, "uid": client.session.uid, "expires_at": client.session.expiry}


@app.get("/api/me")
async def me(client: Annotated[CowboyClient, Depends(get_cowboy_client)]) -> dict:
    await client.ensure_login()
    cache_key = f"me-{client.session.uid or 'anon'}"
    cached = store.load_api_cache(cache_key, PROFILE_CACHE_SECONDS)
    if cached is not None:
        return cached
    try:
        payload = await client.get_me()
        store.save_api_cache(cache_key, payload)
        return payload
    except CowboyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc


@app.get("/api/bikes/{bike_id}")
async def bike(bike_id: int, client: Annotated[CowboyClient, Depends(get_cowboy_client)]) -> dict:
    await client.ensure_login()
    cache_key = f"bike-{bike_id}"
    cached = store.load_api_cache(cache_key, PROFILE_CACHE_SECONDS)
    if cached is not None:
        return cached
    try:
        payload = await client.get_bike(bike_id)
        store.save_api_cache(cache_key, payload)
        return payload
    except CowboyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc


@app.get("/api/me/places")
async def me_places(client: Annotated[CowboyClient, Depends(get_cowboy_client)]) -> dict:
    try:
        return await client.get_me_places()
    except CowboyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc


@app.post("/api/me/push_token")
async def push_token(
    body: Annotated[PushTokenRequest, Body()],
    client: Annotated[CowboyClient, Depends(get_cowboy_client)],
) -> dict:
    try:
        return await client.set_push_token(body.push_token)
    except CowboyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc


@app.post("/api/sync/trips")
async def sync_trips_endpoint(
    body: Annotated[SyncRequest, Body()],
    client: Annotated[CowboyClient, Depends(get_cowboy_client)],
) -> dict:
    try:
        return await sync_trips(
            client,
            store,
            days=body.days,
            overlap_days=body.overlap_days,
            full=body.full,
            workers=body.workers,
            chart_delay=body.chart_delay,
        )
    except CowboyAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.payload or str(exc)) from exc


@app.get("/api/trips")
async def trips() -> list[dict]:
    return store.all_trips()


@app.get("/api/trips/{trip_id}")
async def trip(trip_id: str) -> dict:
    record = store.load_trip_record(trip_id)
    if not record:
        raise HTTPException(status_code=404, detail="Trip not cached.")
    return record


@app.get("/api/heatmap/geojson")
async def heatmap_geojson() -> dict:
    return store.geojson()


@app.get("/api/heatmap/roads")
async def heatmap_roads(grid_m: float = 10.0, date_prefix: str = "", date_from: str = "", date_to: str = "") -> dict:
    if grid_m < 2 or grid_m > 100:
        raise HTTPException(status_code=400, detail="grid_m must be between 2 and 100.")
    return road_frequency_geojson(
        store.all_records(),
        grid_m=grid_m,
        date_prefix=date_prefix,
        date_from=date_from,
        date_to=date_to,
    )


@app.get("/api/metrics/overview")
async def metrics_overview() -> dict:
    return store.overview()
