# TODO: Cowboy Dashboard

Status: 2026-09-15

## Target

- [x] Fetch Cowboy data through a local Python backend, cache it locally, and expose it through a Vue 3 web UI.
- [x] Integrate the heatmap logic inspired by `mmmago/cowboyheatmap`.
- [x] Keep requests to the official Cowboy API as low as possible.
- [x] Provide a mock Cowboy server so tests and demo usage do not call the real API.
- [x] Keep real account data, trip data, raw API dumps, and cache files out of git.

## References

- `https://github.com/sam-dumont/cowboybike-strava-sync/tree/main/src`
- `https://github.com/mmmago/cowboyheatmap`

Both repositories were checked. The trip, chart, and auth endpoints used here come from those implementations.

## Backend

- [x] Implement `CowboyClient` for auth, profile, bike, places, trips, and trip charts.
- [x] Use Android-app-like headers:
  - [x] `X-Cowboy-App-Token`
  - [x] `Client-Type: Android-App`
  - [x] `User-Agent: okhttp/4.9.3`
  - [x] `Content-Type: application/json;charset=utf-8`
- [x] Keep Cowboy auth headers server side.
- [x] Do not store Cowboy passwords in browser storage.
- [x] Keep sessions in memory.
- [x] Implement local backend endpoints for login, sync, trips, heatmap, and metrics.
- [x] Remove speculative reverse-engineering endpoints and raw proxies.
- [ ] Use `ETag` or `Last-Modified` if Cowboy exposes useful cache headers.

## Request Minimization

- [x] Sync only when requested by the user.
- [x] Use incremental trip sync after the first run.
- [x] Use an overlap window to catch late updates.
- [x] Backfill only older missing ranges when the sync range is expanded.
- [x] Fetch trip charts only when they are not cached yet.
- [x] Cache profile and bike responses for a short period.
- [x] Report chart fetch failures and rate limits in sync state.

## Storage

- [x] Use a file based cache first.
- [x] Store one JSON record per trip.
- [x] Store sync state separately.
- [x] Ignore local cache and real JSON exports in git.
- [ ] Consider PostgreSQL later.
- [ ] If PostgreSQL is added, use JSONB for raw chart data and indexed fields for trip dates, bike id, and distance.

## Mock Server

- [x] Provide `app/mock_cowboy.py`.
- [x] Toggle mock mode with `COWBOY_MOCK_SERVER=true`.
- [x] Make tests fail if they accidentally call the real Cowboy API.
- [x] Seed demo profile, bike, trip, and chart data automatically when mock mode starts with an empty local store.

## Heatmap

- [x] Convert Cowboy `[lat, lng]` chart positions to GeoJSON `[lng, lat]`.
- [x] Drop empty or broken GPS points.
- [x] Generate route GeoJSON.
- [x] Generate road-frequency buckets.
- [x] Support date filters.
- [x] Support grid sizes `5 m`, `20 m`, and `50 m`.
- [x] Support weighted frequency rendering and plain route rendering.
- [x] Center the map on the latest ride when no filter is active.

## Web UI

- [x] Use Vue 3, Vuetify, ApexCharts, and MapLibre.
- [x] Build a login page with email and password fields.
- [x] Build a dashboard with bike status, battery state, range, firmware, settings, and location.
- [x] Show total distance, ride time, average speed, power, and CO2 savings.
- [x] Show yearly, monthly, and daily bar charts.
- [x] Drill down from year to month to day by clicking chart bars.
- [x] Filter dashboard stats and heatmap by date range.
- [x] Provide a reset button for filters.
- [x] Provide heatmap controls for grid size and display mode.
- [x] Add dark mode as the default theme.
- [x] Add German and English UI language selection.
- [ ] Improve bundle size with code splitting.

## Docker

- [x] Add Docker Compose for backend and frontend.
- [x] Add backend healthcheck.
- [x] Document cache volume behavior.
- [ ] Add frontend healthcheck.

## Tests

- [x] Test mock server wiring.
- [x] Test that tests do not call the real Cowboy API.
- [x] Test that cached charts are not fetched again.
- [x] Test GeoJSON coordinate conversion.
- [x] Test road-frequency counts.
- [x] Test road-frequency date range filtering.
- [ ] Add tests for automatic mock-store seeding.
- [ ] Add more CowboyClient tests for auth header parsing and 401 re-auth.

## Open Questions

- [ ] Should Strava sync be added later, or is the Strava project only an API reference?
- [ ] Should sessions remain memory-only, or should encrypted server-side session storage be added later?
