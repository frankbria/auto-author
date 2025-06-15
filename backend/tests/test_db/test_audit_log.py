"""Test audit log functionality"""

import pytest
from app.db.audit_log import create_audit_log
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_audit_log():
    """Test creating audit log entries"""
    # Mock the audit_logs_collection
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock()
    
    with patch('app.db.audit_log.audit_logs_collection', mock_collection):
        # Test basic audit log
        log = await create_audit_log(
            action="test_action",
            actor_id="user123",
            target_id="resource456",
            resource_type="test_resource"
        )
        
        assert log["action"] == "test_action"
        assert log["actor_id"] == "user123"
        assert log["target_id"] == "resource456"
        assert log["resource_type"] == "test_resource"
        assert "timestamp" in log
        assert isinstance(log["timestamp"], datetime)
        assert log["details"] == {}
        
        # Verify insert_one was called
        mock_collection.insert_one.assert_called()
        
        # Test with details
        log_with_details = await create_audit_log(
            action="update_book",
            actor_id="user789",
            target_id="book123",
            resource_type="book",
            details={
                "fields_updated": ["title", "description"],
                "previous_title": "Old Title",
                "new_title": "New Title"
            }
        )
        
        assert log_with_details["details"]["fields_updated"] == ["title", "description"]
        assert log_with_details["details"]["new_title"] == "New Title"
        
        # Verify insert_one was called twice
        assert mock_collection.insert_one.call_count == 2