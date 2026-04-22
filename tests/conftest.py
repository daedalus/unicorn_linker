import pytest


@pytest.fixture
def sample_text() -> str:
    """Sample text for testing."""
    return "hello world"


@pytest.fixture
def sample_input() -> dict:
    """Sample input data for testing."""
    return {"text": "test", "max_length": 100}
