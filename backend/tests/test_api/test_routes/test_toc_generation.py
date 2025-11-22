import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock


# Mock TOC response for testing
MOCK_TOC_RESPONSE = {
    "toc": {
        "chapters": [
            {
                "id": "ch1",
                "title": "Introduction",
                "level": 1,
                "order": 1,
                "description": "Introduction to the topic"
            },
            {
                "id": "ch2",
                "title": "Main Content",
                "level": 1,
                "order": 2,
                "description": "Core concepts and ideas"
            }
        ]
    },
    "chapters_count": 2,
    "has_subchapters": False,
    "success": True
}


@pytest.mark.asyncio
@patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
async def test_generate_toc_endpoint(mock_generate_toc, async_client_factory):
    # Configure the mock to return our test TOC
    mock_generate_toc.return_value = MOCK_TOC_RESPONSE
    
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
    
    # Verify the mock was called with correct parameters
    assert mock_generate_toc.called
    call_args = mock_generate_toc.call_args
    assert call_args[0][0] == "This is a test summary for TOC generation."  # summary
    assert len(call_args[0][1]) == 3  # responses

    # Clean up: delete the test book (if endpoint exists)
    await client.delete(f"/api/v1/books/{book_id}")


@pytest.mark.asyncio
@patch("app.services.ai_service.AIService.generate_toc_from_summary_and_responses")
async def test_toc_generation_workflow_e2e(mock_generate_toc, async_client_factory):
    # Configure the mock to return our test TOC
    mock_generate_toc.return_value = MOCK_TOC_RESPONSE
    
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
    # First verify the book still exists and we can access it
    get_book_resp = await client.get(f"/api/v1/books/{book_id}")
    if get_book_resp.status_code != 200:
        print(f"Book GET failed with status: {get_book_resp.status_code}")
        print(f"Response: {get_book_resp.json()}")
    
    summary_resp2 = await client.patch(
        f"/api/v1/books/{book_id}/summary", json={"summary": ""}
    )
    # Debug: Print the response if it's not 400
    if summary_resp2.status_code != 400:
        print(f"Expected 400, got {summary_resp2.status_code}")
        print(f"Response body: {summary_resp2.json()}")
    assert summary_resp2.status_code == 400
    # Now TOC generation should fail again
    # toc_fail_resp3 = await client.post(f"/api/v1/books/{book_id}/generate-toc")
    # assert toc_fail_resp3.status_code == 400

    # 8. Cleanup
    await client.delete(f"/api/v1/books/{book_id}")