"""
Pytest configuration and shared fixtures for ParallaxAI backend tests.
Resets rate-limit counters before each test function so individual tests
have deterministic rate-limit windows.
"""

import pytest
from backend.middleware.rate_limit import reset_rate_limits


@pytest.fixture(autouse=True)
def clear_rate_limits_between_tests():
    reset_rate_limits()
    yield
    reset_rate_limits()

