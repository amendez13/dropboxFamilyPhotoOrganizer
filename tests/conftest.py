"""Shared test fixtures and configuration."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def isolate_keyring():
    """
    Automatically mock keyring module for all tests to prevent tests from accessing
    real system keyring and to ensure test isolation.

    This fixture mocks the keyring module at import time, which ensures that
    TokenStorage.__init__ gets the mocked keyring instead of the real one.
    """
    # Create a mock keyring module
    mock_keyring_module = MagicMock()
    mock_keyring_module.get_password.return_value = None
    mock_keyring_module.set_password.return_value = None
    mock_keyring_module.delete_password.return_value = None

    # Mock it in sys.modules so imports get the mock
    with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
        yield mock_keyring_module


@pytest.fixture
def mock_config_file():
    """Mock config file loading to prevent tests from reading real config.yaml."""
    with patch("builtins.open"), patch("os.path.exists", return_value=False):
        yield
