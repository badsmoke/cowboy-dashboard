# Cowboy App API

Status: 2026-09-15.

This file documents the Cowboy endpoints used by this project. The endpoints were derived from:

- `https://github.com/sam-dumont/cowboybike-strava-sync/tree/main/src`
- `https://github.com/mmmago/cowboyheatmap`

Tests must not call the real Cowboy API. They use `app.mock_cowboy` through an in-process `httpx.ASGITransport`.

Example payloads are anonymized. Personal values such as email addresses, addresses, exact private locations, passkeys, serial numbers, MAC addresses, and tokens are redacted or replaced with mock values.

## Base URL

```text
https://app-api.cowboy.bike
```

## App Headers

The client intentionally uses Android-app-like headers:

```http
Content-Type: application/json;charset=utf-8
Client-Type: Android-App
Client: Android-App
User-Agent: okhttp/4.9.3
X-Cowboy-App-Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
```

After login, protected requests also include:

```http
Client: <client-header-from-login>
Access-Token: <access-token-from-login>
Uid: <uid-from-login>
```

## POST /auth/sign_in

Authenticates with Cowboy app credentials. The important session values are returned as response headers.

Request:

```json
{
  "email": "user@example.invalid",
  "password": "<password>"
}
```

Response headers:

```http
Client: <session-client>
Access-Token: <session-access-token>
Uid: user@example.invalid
Expiry: 1790000000
```

Response body:

```json
{
  "data": {
    "id": 90001,
    "uid": "user@example.invalid",
    "email": "user@example.invalid"
  }
}
```

Typical error: `401` with `errors: ["bad_credentials"]`.

## GET /users/me

Returns the user profile, account settings, total distance, total duration, and the embedded bike object.

Auth: yes.

Example:

```json
{
  "id": 90001,
  "uuid": "<user-uuid>",
  "uid": "user@example.invalid",
  "email": "user@example.invalid",
  "country_code": "DE",
  "total_distance": 2762.480006925687,
  "total_duration": 602097,
  "settings": {
    "distance_units": "kilometers",
    "temperature_units": "celsius",
    "weight_units": "kilograms"
  },
  "bike": {
    "id": 90002,
    "nickname": "Demo Bike",
    "model": {
      "name": "Cowboy 3",
      "description": "Cowboy 3"
    },
    "sku": {
      "code": "DEMO-SKU-BLACK",
      "market": "EU",
      "color": "Black",
      "color_hex": "#0C0D0D",
      "features": {
        "battery_autonomy": 60,
        "battery_leds": 5,
        "available_speeds": {
          "default": 28,
          "offroad": null
        },
        "displayed_speeds": {
          "default": 25,
          "offroad": null
        }
      }
    },
    "stolen": false,
    "crashed": false,
    "passkey": "<redacted>",
    "activated_at": "2022-03-31T12:28:30.583+02:00",
    "firmware_version": "v4.21.5",
    "seen_at": "2026-08-17T13:09:34.762+02:00",
    "last_crash_started_at": "2024-05-25T14:14:28.166+02:00",
    "autonomy": 61.14,
    "battery_state_of_charge": 90,
    "battery_state_of_charge_updated_at": "2026-08-17T13:09:34.762+02:00",
    "battery_inserted": true,
    "pcb_battery_state_of_charge": 91.0,
    "serial_number": "<redacted>",
    "total_distance": 2762.480006925687,
    "total_duration": 602097,
    "total_co2_saved": 345310,
    "position": {
      "latitude": "<redacted>",
      "longitude": "<redacted>",
      "received_at": "2026-08-17T10:27:10.000+02:00",
      "source": "bike",
      "type": "stolen"
    },
    "available_features": {
      "theft_alerts": "available",
      "auto_unlock": "available",
      "crash_detection": "available",
      "trip_analysis": "available",
      "strava": "available"
    },
    "last_ride_mode": "static_eu",
    "autonomies": [
      {
        "ride_mode": "adaptive_eu",
        "full_battery_range": 61.13,
        "calibrated": false
      },
      {
        "ride_mode": "static_eu",
        "full_battery_range": 61.13,
        "calibrated": true
      }
    ],
    "settings": {
      "theft_alerts": true,
      "auto_unlock": true,
      "crash_detection": true,
      "led_brightness": 100,
      "manual_unlock": 10,
      "auto_lock": 5,
      "smart_lock": true,
      "max_speed": 28,
      "brake_light_sensitivity": 10,
      "default_ride_mode": "static_eu"
    }
  }
}
```

Observed top-level fields include:

```text
active_subscriptions, all_possible_plans, available_bikes,
available_languages, available_plans, avatar_url, avatars, bike, biography,
country_code, cover_url, crash_detection, created_at, email,
emergency_phone_number, facebook_profile_url, facebook_username,
first_bike_assigned_at, first_name, human_efficiency_factor, id,
in_app_shop_enabled, instagram_profile_url, instagram_username,
intercom_token, investor_number, last_name, nickname, phone_number,
profile_link, provider, push_token, referral_program, role, settings,
social_features, strava_authorized, subscription, sync_apple_health,
sync_google_fit, sync_strava, total_co2_saved, total_distance, total_duration,
uid, updated_at, uuid
```

## GET /bikes/{bike_id}

Returns bike data for a concrete bike id. The structure is equivalent to the nested `bike` object from `GET /users/me`.

Auth: yes.

Dashboard-relevant fields:

```json
{
  "id": 90002,
  "nickname": "Demo Bike",
  "model": {
    "name": "Cowboy 3"
  },
  "firmware_version": "v4.21.5",
  "seen_at": "2026-08-17T13:09:34.762+02:00",
  "autonomy": 61.14,
  "battery_state_of_charge": 90,
  "battery_state_of_charge_updated_at": "2026-08-17T13:09:34.762+02:00",
  "battery_inserted": true,
  "pcb_battery_state_of_charge": 91.0,
  "total_distance": 2762.480006925687,
  "total_duration": 602097,
  "total_co2_saved": 345310,
  "last_ride_mode": "static_eu"
}
```

Range note: Cowboy exposes multiple range-related values. `sku.features.battery_autonomy`, `bike.autonomy`, and `bike.autonomies[]` can differ from the mobile app display because the app may combine battery state, calibration, and ride mode.

## GET /users/me/places

Returns home, work, saved places, and navigation history.

Auth: yes.

Example:

```json
{
  "home": {
    "id": 1054648,
    "type": "home",
    "place_id": "<redacted>",
    "name": "Home",
    "user_label": "Home",
    "address": "<redacted>",
    "latitude": "<redacted>",
    "longitude": "<redacted>",
    "last_navigated_at": "2022-06-08T15:59:57.452+02:00",
    "full_address": "<redacted>"
  },
  "work": {
    "id": 1054649,
    "type": "work",
    "place_id": "<redacted>",
    "name": "Work",
    "user_label": "Work",
    "address": "<redacted>",
    "latitude": "<redacted>",
    "longitude": "<redacted>",
    "last_navigated_at": "2022-05-02T15:27:15.770+02:00",
    "full_address": "<redacted>"
  },
  "saved": [],
  "history": [
    {
      "id": 1054643,
      "type": "history",
      "place_id": "<redacted>",
      "name": "Demo Stop",
      "user_label": null,
      "address": "<redacted>",
      "latitude": "<redacted>",
      "longitude": "<redacted>",
      "last_navigated_at": "2022-03-31T19:36:28.689+02:00",
      "full_address": "<redacted>"
    }
  ]
}
```

Observed top-level fields:

```text
home, work, saved, history
```

## POST /users/me/push_token

Registers a push token for the app.

Auth: yes.

Request:

```json
{
  "push_token": "<push-token>"
}
```

Any `2xx` response is treated as success by this project.

## GET /trips

Lists trips in pages. The reference implementations send filters as a JSON body on a `GET` request.

Auth: yes.

Request body:

```json
{
  "page": 1,
  "from": "2025-01-01T00:00:00",
  "to": "2026-09-16T00:00:00"
}
```

Shortened response:

```json
{
  "last_page": false,
  "daily_summaries": {
    "2026-08-17": {
      "distance": 4.2,
      "duration": 1260,
      "trips": [
        {
          "id": 42001,
          "uid": "mock-trip-42001",
          "title": "Morning Ride",
          "started_at": "2026-08-17T08:10:00Z",
          "ended_at": "2026-08-17T08:31:00Z",
          "distance": 4.2,
          "unlocked_time": 1260,
          "moving_time": 1180,
          "average_user_power": 92,
          "average_motor_power": 104,
          "has_dashboard_data": true
        }
      ]
    }
  }
}
```

Observed trip fields:

```text
average_motor_power, average_moving_velocity, average_user_power,
average_velocity, bike_id, calories_burned, co2_saved, created_at, distance,
duration, ended_at, force_ended, has_dashboard_data, id, moving_time,
position, route, started_at, title, total_motor_energy, total_user_energy,
trip_share_summary, uid, unlocked_time, upload_status
```

Sync strategy:

```text
First sync: list the requested range and fetch all missing charts.
Later sync: list only the recent range plus an overlap window.
Backfill: when the requested range is expanded, list only the older missing range.
Charts: fetch a trip chart only when it is not already stored locally.
```

## GET /trips/{trip_id}

Returns a single trip. The Strava reference project uses this endpoint when a concrete activity is re-uploaded.

Auth: yes.

Response: one trip object as seen in `GET /trips`.

## GET /trips/{trip_id}/charts

Returns dashboard and route data for a trip. `positions` is the important field for the heatmap. Cowboy returns positions as `[lat, lng]`; GeoJSON and MapLibre use `[lng, lat]`.

Auth: yes.

Shortened response:

```json
{
  "positions": [
    ["<lat-redacted>", "<lng-redacted>"],
    ["<lat-redacted>", "<lng-redacted>"],
    ["<lat-redacted>", "<lng-redacted>"]
  ],
  "durations": [0, 1, 2],
  "distances": [0, 0, 0],
  "charts": {
    "heart_rate_data": [],
    "user_power": [],
    "vehicle_speed": []
  }
}
```

## Mock Server

The mock server lives in:

```text
app/mock_cowboy.py
```

Enable it with:

```bash
COWBOY_MOCK_SERVER=true
```

Truthy values are `true`, `1`, `yes`, and `on`. Any other value, including `false`, uses the official Cowboy API.

The mock implements:

```text
POST /auth/sign_in
GET  /users/me
GET  /bikes/{bike_id}
GET  /users/me/places
POST /users/me/push_token
GET  /trips
GET  /trips/{trip_id}
GET  /trips/{trip_id}/charts
```

When mock mode is enabled and the local trip store is empty, the backend seeds mock trips and chart data on startup. This makes the dashboard usable without a first real sync.

Tests use the mock in process:

```python
transport = httpx.ASGITransport(app=mock_cowboy_app)
client = CowboyClient(
    "mock-user@example.invalid",
    "password",
    base_url="http://mock-cowboy",
    transport=transport,
)
```

The tests also patch `httpx.AsyncHTTPTransport.handle_async_request`. If a test accidentally uses the real HTTP transport, it fails instead of calling `https://app-api.cowboy.bike`.
