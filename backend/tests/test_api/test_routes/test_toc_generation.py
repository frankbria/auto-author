import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_generate_toc_endpoint(async_client_factory):
    client = await async_client_factory()
    # Create a test book first (assuming endpoint exists and returns book_id)
    book_data = {
        "title": "Integration Test Book",
        "description": "A book for integration testing TOC generation.",
        "genre": "Test",
        "target_audience": "Developers",
    }
    create_resp = await client.post("/api/v1/books/", json=book_data)
    assert create_resp.status_code == 201
    book_id = create_resp.json()["id"]

    # Provide a summary to enable TOC generation
    summary_data = {"summary": "This is a test summary for TOC generation."}
    summary_resp = await client.patch(
        f"/api/v1/books/{book_id}/summary", json=summary_data
    )
    assert summary_resp.status_code == 200

    # Provide dummy clarifying question responses
    responses = [
        {"question": "Q1", "answer": "Answer 1"},
        {"question": "Q2", "answer": "Answer 2"},
        {"question": "Q3", "answer": "Answer 3"},
    ]
    qr_resp = await client.put(
        f"/api/v1/books/{book_id}/question-responses", json={"responses": responses}
    )
    assert qr_resp.status_code == 200

    # Call the TOC generation endpoint
    toc_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    assert toc_resp.status_code == 200
    toc_json = toc_resp.json()
    assert "toc" in toc_json
    assert toc_json["success"] is True
    assert toc_json["toc"]["chapters"]

    # Clean up: delete the test book (if endpoint exists)
    await client.delete(f"/api/v1/books/{book_id}")


@pytest.mark.asyncio
async def test_toc_generation_workflow_e2e(async_client_factory):
    client = await async_client_factory()
    # 1. Create a book
    book_data = {
        "title": "E2E Test Book",
        "description": "A book for E2E TOC workflow testing.",
        "genre": "Science",
        "target_audience": "Students",
    }
    create_resp = await client.post("/api/v1/books/", json=book_data)
    assert create_resp.status_code == 201
    book_id = create_resp.json()["id"]

    # 2. Try generating TOC before summary (should fail)
    toc_fail_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    assert toc_fail_resp.status_code == 400
    assert "summary is required" in toc_fail_resp.text.lower()

    # 3. Submit a summary
    summary_data = {
        "summary": "This is a comprehensive summary for E2E TOC generation."
    }
    summary_resp = await client.patch(
        f"/api/v1/books/{book_id}/summary", json=summary_data
    )
    assert summary_resp.status_code == 200

    # 4. Try generating TOC before clarifying question responses (should fail)
    toc_fail_resp2 = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    assert toc_fail_resp2.status_code == 400
    assert "question responses are required" in toc_fail_resp2.text.lower()

    # 5. Submit clarifying question responses
    responses = [
        {"question": "What is the main focus?", "answer": "Physics concepts"},
        {"question": "Who is the audience?", "answer": "High school students"},
    ]
    qr_resp = await client.put(
        f"/api/v1/books/{book_id}/question-responses", json={"responses": responses}
    )
    assert qr_resp.status_code == 200

    # 6. Generate TOC (should succeed)
    toc_resp = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    assert toc_resp.status_code == 200
    toc_json = toc_resp.json()
    assert toc_json["success"] is True
    assert "toc" in toc_json
    assert toc_json["toc"]["chapters"]

    # 7. Try submitting empty summary (should fail validation)
    summary_resp2 = await client.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": ""}
    )
    assert summary_resp2.status_code == 400
    # Now TOC generation should fail again
    # toc_fail_resp3 = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    # assert toc_fail_resp3.status_code == 400

    # 8. Cleanup
    await client.delete(f"/api/v1/books/{book_id}")
