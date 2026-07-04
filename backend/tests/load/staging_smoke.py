"""Low-impact staging load smoke for GitHub Actions.

This file is intentionally separate from ``locustfile.py`` because staging uses
Better Auth cookie sessions and the public frontend/API hosts. It exercises the
staging auth boundary plus cheap API endpoints without repeatedly triggering AI
work or creating high request volume.
"""

from __future__ import annotations

import os
import time
from typing import Any

from locust import HttpUser, between, task


STAGING_API_URL = os.getenv("STAGING_API_URL", "https://api.dev.autoauthor.app/api/v1")
STAGING_TEST_EMAIL = os.getenv("STAGING_TEST_EMAIL") or os.getenv("TEST_USER_EMAIL")
STAGING_TEST_PASSWORD = os.getenv("STAGING_TEST_PASSWORD") or os.getenv("TEST_USER_PASSWORD")
AUTH_FAILURE_STATUSES = {401, 403}


class StagingSmokeUser(HttpUser):
    """Authenticated, low-volume staging API smoke user."""

    wait_time = between(2, 5)

    def on_start(self) -> None:
        if not STAGING_TEST_EMAIL or not STAGING_TEST_PASSWORD:
            raise RuntimeError(
                "Set STAGING_TEST_EMAIL/STAGING_TEST_PASSWORD or TEST_USER_EMAIL/TEST_USER_PASSWORD"
            )

        self.book_id: str | None = None
        self._sign_in()
        self._ensure_book()

    def _sign_in(self) -> None:
        with self.client.post(
            "/api/auth/sign-in/email",
            json={
                "email": STAGING_TEST_EMAIL,
                "password": STAGING_TEST_PASSWORD,
                "callbackURL": "/dashboard",
            },
            name="better-auth sign-in",
            catch_response=True,
        ) as response:
            if response.status_code >= 400:
                response.failure(f"sign-in returned {response.status_code}: {response.text[:300]}")
                raise RuntimeError("Better Auth sign-in failed during staging load smoke")
            response.success()

    def _api(self, path: str) -> str:
        return f"{STAGING_API_URL.rstrip('/')}/{path.lstrip('/')}"

    def _ensure_book(self) -> None:
        title = f"Load Smoke Book {int(time.time())}"
        with self.client.post(
            self._api("/books/"),
            json={"title": title, "description": "Created by low-impact staging load smoke."},
            name="POST /api/v1/books/",
            catch_response=True,
        ) as response:
            if response.status_code in AUTH_FAILURE_STATUSES:
                response.failure(f"book create auth failed with {response.status_code}")
                raise RuntimeError("Authenticated book create failed during staging load smoke")
            if response.status_code >= 500:
                response.failure(f"book create returned {response.status_code}: {response.text[:300]}")
                return
            if response.status_code < 400:
                payload: dict[str, Any] = response.json()
                self.book_id = payload.get("id") or payload.get("_id")
            response.success()

    @task(4)
    def list_books(self) -> None:
        with self.client.get(
            self._api("/books/"),
            name="GET /api/v1/books/",
            catch_response=True,
        ) as response:
            if response.status_code in AUTH_FAILURE_STATUSES:
                response.failure(f"list books auth failed with {response.status_code}")
            elif response.status_code >= 500:
                response.failure(f"list books returned {response.status_code}")
            else:
                response.success()

    @task(2)
    def health(self) -> None:
        with self.client.get(
            self._api("/health"),
            name="GET /api/v1/health",
            catch_response=True,
        ) as response:
            if response.status_code >= 500:
                response.failure(f"health returned {response.status_code}")
            else:
                response.success()

    @task(1)
    def toc_readiness_boundary(self) -> None:
        if not self.book_id:
            return

        with self.client.get(
            self._api(f"/books/{self.book_id}/toc-readiness"),
            name="GET /api/v1/books/:id/toc-readiness",
            catch_response=True,
        ) as response:
            # 400/404 is acceptable when the smoke-created book has no summary;
            # auth failures and 5xx responses indicate staging instability.
            if response.status_code in AUTH_FAILURE_STATUSES:
                response.failure(f"toc readiness auth failed with {response.status_code}")
            elif response.status_code >= 500:
                response.failure(f"toc readiness returned {response.status_code}")
            else:
                response.success()
