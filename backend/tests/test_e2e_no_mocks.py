"""Test E2E without any mocks to see actual errors"""

import pytest
import os
from tests.test_system_e2e import SystemE2ETest, TEST_TIMEOUT


@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OpenAI API key - skipping in CI/CD without key"
)
async def test_complete_system_workflow_no_mocks(auth_client_factory):
    """Test the complete authoring workflow without any mocks"""
    client = await auth_client_factory()
    test = SystemE2ETest(client, cleanup=True)
    await test.run()