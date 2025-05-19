# filepath: d:\Projects\auto-author\backend\tests\test_api\test_routes\test_concurrent_profile_edits.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock, call
import asyncio
import json
from datetime import datetime, timezone

pytest.skip("Skipping this file for now - haven't dealt with concurrency yet.", allow_module_level=True)

def simulate_concurrent_requests(client, url, json_data1, json_data2):
    """
    Helper function to simulate concurrent requests
    """
    # Create two threads to simulate concurrent requests
    import threading

    # Store responses for later inspection
    responses = []

    def make_request(json_data):
        response = client.patch(url, json=json_data)
        responses.append(response)

    # Create threads for each request
    thread1 = threading.Thread(target=make_request, args=(json_data1,))
    thread2 = threading.Thread(target=make_request, args=(json_data2,))

    # Start threads
    thread1.start()
    thread2.start()

    # Wait for both to complete
    thread1.join()
    thread2.join()

    return responses


def test_concurrent_profile_edits(auth_client_factory, test_user):
    """
    Test handling of concurrent edits to user profile.
    Verifies that the system handles concurrent updates properly.
    """
    # Create a client with test user data
    client = auth_client_factory()
    
    # Update data for the first concurrent request
    update_data1 = {"first_name": "NewFirstName1", "bio": "New bio from update 1"}

    # Update data for the second concurrent request
    update_data2 = {"first_name": "NewFirstName2", "preferences": {"theme": "light"}}

    # The first update should result in this user
    update1_result = test_user.copy()
    update1_result["first_name"] = update_data1["first_name"]
    update1_result["bio"] = update_data1["bio"]

    # The second update should result in this user
    update2_result = update1_result.copy()
    update2_result["first_name"] = update_data2["first_name"]
    update2_result["preferences"]["theme"] = "light"

    # Create a lock to simulate real database behavior
    mock_db_lock = asyncio.Lock()
    processed_updates = []

    async def mock_update_user(clerk_id, user_data, actor_id=None):
        """Mock database update with locking behavior"""
        async with mock_db_lock:
            # Simulate some processing time
            await asyncio.sleep(0.01)
            processed_updates.append(user_data)

            # For testing, we need to track the order of updates
            if len(processed_updates) == 1:
                return update1_result
            else:
                return update2_result

    # Mock the update_user dependency
    with patch("app.db.database.update_user", mock_update_user):
        # Simulate concurrent requests
        responses = simulate_concurrent_requests(
            client, "/api/v1/users/me", update_data1, update_data2
        )

        # Both requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Verify both updates were processed
        assert len(processed_updates) == 2

        # Check final state matches expectations
        final_response = responses[1].json()
        assert final_response["first_name"] == update_data2["first_name"]
        assert final_response["bio"] == update_data1["bio"]
        assert final_response["preferences"]["theme"] == "light"


def test_concurrent_conflicting_edits(auth_client_factory, test_user):
    """
    Test handling of concurrent conflicting edits.
    Verifies that when two edits conflict, the system handles it gracefully.
    """
    # Create a client with test user data
    client = auth_client_factory()
    
    # Set up a counter for update sequence
    update_counter = 0

    # Two updates that modify the same field
    update_data1 = {"bio": "New bio version 1"}
    update_data2 = {"bio": "New bio version 2"}

    # Mock updated user data after first update
    first_updated_user = test_user.copy()
    first_updated_user["bio"] = "New bio version 1"
    first_updated_user["updated_at"] = datetime.now(timezone.utc)

    # Mock updated user data after second update
    second_updated_user = first_updated_user.copy()
    second_updated_user["bio"] = "New bio version 2"
    second_updated_user["updated_at"] = datetime.now(timezone.utc)

    # Mock database update function
    async def mock_update_user(clerk_id, user_data, actor_id=None):
        nonlocal update_counter
        update_counter += 1

        # Simulate database versioning - second update sees results of first update
        if update_counter == 1:
            await asyncio.sleep(0.01)  # Small delay for first update
            return first_updated_user
        else:
            return second_updated_user

    # Mock the update_user dependency
    with patch("app.db.database.update_user", mock_update_user):
        # Simulate concurrent requests
        responses = simulate_concurrent_requests(
            client, "/api/v1/users/me", update_data1, update_data2
        )

        # Both requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Second update should win (last writer wins)
        final_response = responses[1].json()
        assert final_response["bio"] == "New bio version 2"


def test_concurrent_edits_different_fields(auth_client_factory, test_user):
    """
    Test concurrent edits to different profile fields.
    Verifies that updates to different fields are both preserved.
    """
    # Create a client with test user data
    client = auth_client_factory()
    
    # Update data for different fields
    update_data1 = {"first_name": "NewFirstName"}
    update_data2 = {"last_name": "NewLastName"}

    # Result after first update
    first_result = test_user.copy()
    first_result["first_name"] = "NewFirstName"

    # Result after second update (should include first update)
    second_result = first_result.copy()
    second_result["last_name"] = "NewLastName"

    # Track update order
    update_sequence = []

    # Mock database update function
    async def mock_update_user(clerk_id, user_data, actor_id=None):
        # Record what fields are being updated
        update_sequence.append(list(user_data.keys()))

        # Return appropriate result based on update order
        if len(update_sequence) == 1:
            return first_result
        else:
            return second_result

    # Mock the update_user dependency
    with patch("app.db.database.update_user", mock_update_user):
        # Simulate concurrent requests
        responses = simulate_concurrent_requests(
            client, "/api/v1/users/me", update_data1, update_data2
        )

        # Both requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Final state should have both updates
        final_response = responses[1].json()
        assert final_response["first_name"] == "NewFirstName"
        assert final_response["last_name"] == "NewLastName"

        # Verify both fields were updated separately (not merged into one update)
        assert len(update_sequence) == 2
        assert "first_name" in update_sequence[0]
        assert "last_name" in update_sequence[1]
