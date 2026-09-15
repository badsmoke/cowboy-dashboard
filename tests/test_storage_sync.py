from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import httpx

from app.cowboy import CowboyClient
from app.main import create_cowboy_client, mock_server_enabled, seed_mock_store_if_needed
from app.storage import TripStore
from app.heatmap import road_frequency_geojson
from app.mock_cowboy import app as mock_cowboy_app
from app.sync import sync_trips


class FakeCowboyClient:
    def __init__(self) -> None:
        self.chart_calls = 0
        self.list_calls = []

    async def list_trips(self, start, end, page=1):
        self.list_calls.append((start, end, page))
        return {
            "last_page": True,
            "daily_summaries": {
                "2026-09-14": {
                    "trips": [
                        {
                            "id": 42,
                            "uid": "trip-42",
                            "title": "Morning ride",
                            "started_at": "2026-09-14T08:00:00Z",
                            "distance": 3.5,
                            "unlocked_time": 900,
                            "has_dashboard_data": True,
                        }
                    ]
                }
            },
        }

    async def get_trip_charts(self, trip_id):
        self.chart_calls += 1
        return {
            "positions": [[0.0100, 0.0200], [0.0200, 0.0300]],
            "durations": [0, 900],
            "distances": [0, 3500],
        }


class TripStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_server_env_switch_creates_mock_client(self):
        with patch.dict("os.environ", {"COWBOY_MOCK_SERVER": "true"}):
            self.assertTrue(mock_server_enabled())
            client = create_cowboy_client("mock-user@example.invalid", "password")
            self.assertEqual(str(client.http.base_url), "http://mock-cowboy")
            await client.login()
            self.assertEqual(client.session.uid, "mock-user@example.invalid")
            await client.close()

    async def test_mock_server_env_switch_defaults_to_official_client(self):
        with patch.dict("os.environ", {"COWBOY_MOCK_SERVER": "false"}):
            self.assertFalse(mock_server_enabled())
            client = create_cowboy_client("mock-user@example.invalid", "password")
            self.assertEqual(str(client.http.base_url), "https://app-api.cowboy.bike")
            await client.close()

    async def test_mock_mode_seeds_empty_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_store = TripStore(tmpdir)
            with patch.dict("os.environ", {"COWBOY_MOCK_SERVER": "true"}), patch("app.main.store", temp_store):
                seed_mock_store_if_needed()

            overview = temp_store.overview()
            self.assertEqual(overview["trip_count"], 2)
            self.assertEqual(overview["route_count"], 2)
            self.assertTrue(overview["sync"]["mock"])
            self.assertNotEqual(overview["sync"]["finished_at"], "mock")
            datetime.fromisoformat(overview["sync"]["finished_at"].replace("Z", "+00:00"))

    async def test_mock_mode_repairs_legacy_mock_sync_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_store = TripStore(tmpdir)
            temp_store.save_trip_charts(
                {"id": 1, "started_at": "2026-09-14T08:00:00Z"},
                {"positions": [[0.0100, 0.0200], [0.0200, 0.0300]]},
            )
            temp_store.save_sync_state({"started_at": "mock", "finished_at": "mock", "mock": True})

            with patch.dict("os.environ", {"COWBOY_MOCK_SERVER": "true"}), patch("app.main.store", temp_store):
                seed_mock_store_if_needed()

            sync = temp_store.overview()["sync"]
            self.assertTrue(sync["mock"])
            self.assertEqual(sync["listed_trips"], 2)
            self.assertNotEqual(sync["finished_at"], "mock")
            datetime.fromisoformat(sync["finished_at"].replace("Z", "+00:00"))

    async def test_cowboy_client_uses_mock_server(self):
        transport = httpx.ASGITransport(app=mock_cowboy_app)
        client = CowboyClient(
            "mock-user@example.invalid",
            "correct-horse-battery-staple",
            base_url="http://mock-cowboy",
            transport=transport,
        )

        with patch(
            "httpx.AsyncHTTPTransport.handle_async_request",
            side_effect=AssertionError("Tests must not call the real Cowboy API"),
        ):
            me = await client.get_me()
            bike = await client.get_bike(me["bike"]["id"])
            places = await client.get_me_places()
            trips = await client.list_trips(
                start=datetime(2025, 1, 1),
                end=datetime(2027, 1, 1),
            )
            charts = await client.get_trip_charts(42001)

        await client.close()

        self.assertEqual(me["bike"]["nickname"], "Demo Bike")
        self.assertEqual(bike["firmware_version"], "v4.21.5")
        self.assertIn("history", places)
        self.assertFalse(trips["last_page"])
        self.assertGreaterEqual(len(charts["positions"]), 2)

    async def test_sync_runs_against_mock_server_without_real_network(self):
        transport = httpx.ASGITransport(app=mock_cowboy_app)
        client = CowboyClient(
            "mock-user@example.invalid",
            "correct-horse-battery-staple",
            base_url="http://mock-cowboy",
            transport=transport,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = TripStore(tmpdir)
            with patch(
                "httpx.AsyncHTTPTransport.handle_async_request",
                side_effect=AssertionError("Tests must not call the real Cowboy API"),
            ):
                first = await sync_trips(client, store, days=800, full=True)
                second = await sync_trips(client, store, days=800, full=True)

            self.assertEqual(first["listed_trips"], 2)
            self.assertEqual(first["charts_fetched"], 2)
            self.assertEqual(second["charts_fetched"], 0)
            self.assertEqual(store.overview()["route_count"], 2)

        await client.close()

    async def test_sync_does_not_refetch_cached_charts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TripStore(tmpdir)
            client = FakeCowboyClient()

            first = await sync_trips(client, store, days=30, full=True)
            second = await sync_trips(client, store, days=30, full=True)

            self.assertEqual(first["charts_fetched"], 1)
            self.assertEqual(second["charts_fetched"], 0)
            self.assertEqual(client.chart_calls, 1)

    async def test_expanding_sync_window_backfills_missing_old_range(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TripStore(tmpdir)
            client = FakeCowboyClient()

            await sync_trips(client, store, days=30, full=True)
            state = await sync_trips(client, store, days=5000, full=False)

            labels = [window["label"] for window in state["listed_windows"]]
            self.assertIn("recent", labels)
            self.assertIn("backfill", labels)
            self.assertLess(
                client.list_calls[-1][0],
                client.list_calls[-2][0],
            )

    async def test_geojson_flips_lat_lng_to_lng_lat(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TripStore(tmpdir)
            client = FakeCowboyClient()
            await sync_trips(client, store, days=30, full=True)

            geojson = store.geojson()
            coordinates = geojson["features"][0]["geometry"]["coordinates"]

            self.assertEqual(coordinates, [[0.0200, 0.0100], [0.0300, 0.0200]])

    async def test_road_frequency_counts_shared_stretches_once_per_trip(self):
        records = [
            {
                "trip": {"id": 1, "started_at": "2026-09-14T08:00:00Z"},
                "charts": {"positions": [[0.0100, 0.0200], [0.0101, 0.0201], [0.0102, 0.0202]]},
            },
            {
                "trip": {"id": 2, "started_at": "2026-09-14T09:00:00Z"},
                "charts": {"positions": [[0.0100, 0.0200], [0.0101, 0.0201], [0.0102, 0.0202]]},
            },
        ]

        heatmap = road_frequency_geojson(records, grid_m=5)
        counts = [feature["properties"]["count"] for feature in heatmap["features"]]

        self.assertGreater(len(counts), 0)
        self.assertEqual(max(counts), 2)
        self.assertEqual(heatmap["properties"]["trips"], 2)

    async def test_road_frequency_filters_date_range(self):
        records = [
            {
                "trip": {"id": 1, "started_at": "2026-09-14T08:00:00Z"},
                "charts": {"positions": [[0.0100, 0.0200], [0.0101, 0.0201]]},
            },
            {
                "trip": {"id": 2, "started_at": "2025-08-14T08:00:00Z"},
                "charts": {"positions": [[0.0300, 0.0400], [0.0301, 0.0401]]},
            },
        ]

        heatmap = road_frequency_geojson(records, grid_m=5, date_from="2026-01-01", date_to="2026-12-31")

        self.assertEqual(heatmap["properties"]["trips"], 1)


if __name__ == "__main__":
    unittest.main()
