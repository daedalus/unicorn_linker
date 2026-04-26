import pytest


@pytest.fixture
def sample_text() -> str:
    """Sample text for testing."""
    return "hello world"
