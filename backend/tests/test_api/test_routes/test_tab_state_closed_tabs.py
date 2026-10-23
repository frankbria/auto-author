"""Closing a chapter tab hides it until reopened, so the saved tab state carries
`closed_tab_ids` (#1043). Old saved states without the field read back as []."""

import pytest

API = "/api/v1/books"
BASE = {"active_chapter_id": "c1", "open_tab_ids": ["c1"], "tab_order": ["c1"]}


async def _book(api):
    r = await api.post(f"{API}/", json={"title": "Tabs", "genre": "Fiction"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.mark.asyncio
async def test_closed_tab_ids_are_stored_and_returned(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book(api)

    s = await api.post(f"{API}/{book_id}/chapters/tab-state", json={**BASE, "closed_tab_ids": ["c2", "c3"]})
    assert s.status_code == 200, s.text

    r = await api.get(f"{API}/{book_id}/chapters/tab-state")
    assert r.json()["tab_state"]["closed_tab_ids"] == ["c2", "c3"]


@pytest.mark.asyncio
async def test_a_state_saved_without_the_field_reads_back_empty(auth_client_factory):
    api = await auth_client_factory()
    book_id = await _book(api)

    assert (await api.post(f"{API}/{book_id}/chapters/tab-state", json=BASE)).status_code == 200

    r = await api.get(f"{API}/{book_id}/chapters/tab-state")
    assert r.json()["tab_state"]["closed_tab_ids"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "closed",
    [
        [f"c{i}" for i in range(501)],  # too many
        ["c2", "c2"],  # duplicate
        ["x" * 65],  # id too long
        [1],  # not a string
        "c2",  # not a list
    ],
)
async def test_invalid_closed_tab_ids_are_rejected(auth_client_factory, closed):
    api = await auth_client_factory()
    book_id = await _book(api)

    r = await api.post(f"{API}/{book_id}/chapters/tab-state", json={**BASE, "closed_tab_ids": closed})
    assert r.status_code == 422
