from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


APP_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
BASE_URL = "https://app-api.cowboy.bike"
DEFAULT_HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "Client-Type": "Android-App",
    "User-Agent": "okhttp/4.9.3",
    "X-Cowboy-App-Token": APP_TOKEN,
}


class CowboyAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str, payload: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass
class CowboySession:
    client: str = ""
    access_token: str = ""
    uid: str = ""
    expiry: int = 0

    @property
    def is_valid(self) -> bool:
        return bool(self.client and self.access_token and self.uid) and self.expiry > int(time.time())


class CowboyClient:
    def __init__(
        self,
        email: str,
        password: str,
        base_url: str = BASE_URL,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.email = email
        self.password = password
        self.session = CowboySession()
        self.http = httpx.AsyncClient(
            base_url=base_url,
            timeout=30,
            headers=DEFAULT_HEADERS,
            transport=transport,
        )

    async def close(self) -> None:
        await self.http.aclose()

    async def ensure_login(self) -> None:
        await self._ensure_login()

    async def login(self) -> None:
        response = await self.http.post(
            "/auth/sign_in",
            json={"email": self.email, "password": self.password},
            headers={"Client": "Android-App"},
        )
        if response.status_code != 200:
            raise self._error_from_response(response, "Cowboy login failed")

        expiry = response.headers.get("expiry") or response.headers.get("Expiry") or "0"
        self.session = CowboySession(
            client=response.headers.get("client", ""),
            access_token=response.headers.get("access-token", ""),
            uid=response.headers.get("uid", ""),
            expiry=int(expiry),
        )
        if not self.session.client or not self.session.access_token or not self.session.uid:
            raise CowboyAPIError(502, "Cowboy login response did not include auth headers")

    async def get_me(self) -> dict[str, Any]:
        return await self._request("GET", "/users/me")

    async def get_bike(self, bike_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/bikes/{bike_id}")

    async def get_me_places(self) -> dict[str, Any]:
        return await self._request("GET", "/users/me/places")

    async def set_push_token(self, push_token: str) -> dict[str, Any]:
        return await self._request("POST", "/users/me/push_token", json={"push_token": push_token})

    async def list_trips(
        self,
        start: datetime,
        end: datetime,
        page: int = 1,
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/trips",
            json={
                "page": page,
                "from": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "to": end.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )

    async def get_trip(self, trip_id: int | str) -> dict[str, Any]:
        return await self._request("GET", f"/trips/{trip_id}")

    async def get_trip_charts(self, trip_id: int | str) -> dict[str, Any]:
        return await self._request("GET", f"/trips/{trip_id}/charts")

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        await self._ensure_login()
        response = await self.http.request(method, path, headers=self._auth_headers(), json=json, params=params)

        if response.status_code == 401:
            await self.login()
            response = await self.http.request(method, path, headers=self._auth_headers(), json=json, params=params)

        if response.status_code < 200 or response.status_code >= 300:
            raise self._error_from_response(response, "Cowboy API request failed")

        data = response.json()
        return data

    async def _ensure_login(self) -> None:
        if not self.session.is_valid:
            await self.login()

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Client": self.session.client,
            "Access-Token": self.session.access_token,
            "Uid": self.session.uid,
        }

    @staticmethod
    def _error_from_response(response: httpx.Response, fallback: str) -> CowboyAPIError:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text

        message = fallback
        if isinstance(payload, dict):
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                message = "; ".join(str(error) for error in errors)
            elif isinstance(errors, str):
                message = errors
            elif isinstance(payload.get("error"), str):
                message = payload["error"]

        return CowboyAPIError(response.status_code, message, payload)
