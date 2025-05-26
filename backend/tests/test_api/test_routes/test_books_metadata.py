import pytest, pytest_asyncio
from httpx import AsyncClient
from app.main import app
from fastapi.encoders import jsonable_encoder

import asyncio


@pytest.mark.asyncio
async def test_book_metadata_edge_cases(async_client_factory, test_book):

    app.dependency_overrides.clear()

    loop = asyncio.get_event_loop()
    if loop.is_closed():
        pytest.skip("Event loop is closed, skipping async test")

    api_client = await async_client_factory()

    try:
        payload = test_book.copy()
        payload["owner_id"] = str(test_book["owner_id"])
        del payload["_id"]
        del payload["id"]
        # del payload["created_at"]
        # del payload["updated_at"]
        del payload["toc_items"]
        del payload["published"]
        payload_book = jsonable_encoder(payload)
        # print(payload_book)

        # Insert book into the database
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        assert response.status_code == 201
        new_id = response.json()["id"]

        # Long fields
        long_title = "A" * 101
        response = await api_client.patch(
            f"/api/v1/books/{new_id}", json={"title": long_title}
        )
        assert response.status_code == 422  # Should fail validation

        # Special characters
        special = "!@#$%^&*()_+{}|:<>?~"
        response = await api_client.patch(
            f"/api/v1/books/{new_id}", json={"title": special}
        )
        assert response.status_code == 200
        assert response.json()["title"] == special

        # Concurrent edits (simulate by rapid PATCH)
        patch1 = api_client.patch(
            f"/api/v1/books/{new_id}", json={"title": "Concurrent 1"}
        )
        patch2 = api_client.patch(
            f"/api/v1/books/{new_id}", json={"title": "Concurrent 2"}
        )
        results = await asyncio.gather(patch1, patch2)
        assert all(r.status_code == 200 for r in results)

    finally:
        await api_client.aclose()
        # Clean up the database


@pytest.mark.asyncio
async def test_book_metadata_retrieval_and_update(auth_client_factory, test_book):
    # Test GET book metadata
    api_client = await auth_client_factory()
    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    # del payload["created_at"]
    # del payload["updated_at"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)
    # print(payload_book)

    # Insert book into the database
    response = await api_client.post(f"/api/v1/books/", json=payload_book)
    assert response.status_code == 201
    new_id = response.json()["id"]

    response = await api_client.get(f"/api/v1/books/{new_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == test_book["title"]
    assert "target_audience" in data

    # Test PATCH update
    patch_data = {"title": "Updated Title", "target_audience": "academic"}
    response = await api_client.patch(f"/api/v1/books/{new_id}", json=patch_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["target_audience"] == "academic"

    # Test PUT update
    put_data = {
        "title": "Put Title",
        "target_audience": "professional",
        "genre": "science",
    }
    response = await api_client.put(f"/api/v1/books/{new_id}", json=put_data)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Put Title"
    assert data["target_audience"] == "professional"
    assert data["genre"] == "science"


@pytest.mark.asyncio
async def test_book_metadata_persistence(auth_client_factory, test_book):
    api_client = await auth_client_factory()
    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    # del payload["created_at"]
    # del payload["updated_at"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)
    # print(payload_book)
    # Insert book into the database
    response = await api_client.post(f"/api/v1/books/", json=payload_book)
    assert response.status_code == 201
    new_id = response.json()["id"]

    # Update and reload
    response = await api_client.patch(
        f"/api/v1/books/{new_id}", json={"title": "Persistence Test"}
    )
    assert response.status_code == 200
    # Simulate reload
    response = await api_client.get(f"/api/v1/books/{new_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Persistence Test"


# Mark as done: Test retrieval and update of book metadata via API
# Mark as done: Test edge cases (long fields, special characters, concurrent edits)
# Mark as done: Verify metadata changes persist between sessions and reloads
