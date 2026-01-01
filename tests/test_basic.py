"""Basic tests to ensure the test infrastructure is working."""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_python_version():
    """Test that we're running on a supported Python version."""
    assert sys.version_info >= (3, 10), "Python 3.10 or higher is required"


def test_imports():
    """Test that core dependencies can be imported."""
    import yaml
    import dropbox
    from PIL import Image

    assert yaml is not None
    assert dropbox is not None
    assert Image is not None


def test_config_example_exists():
    """Test that the example configuration file exists."""
    config_path = Path(__file__).parent.parent / "config" / "config.example.yaml"
    assert config_path.exists(), "config.example.yaml should exist"


def test_config_example_valid():
    """Test that the example configuration file is valid YAML."""
    import yaml

    config_path = Path(__file__).parent.parent / "config" / "config.example.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert 'dropbox' in config
    assert 'source_folder' in config['dropbox']
    assert 'destination_folder' in config['dropbox']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
