"""Unit tests for train_face_model script."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from train_face_model import get_reference_photos, load_config, main  # noqa: E402


class TestLoadConfig:
    """Test load_config function."""

    @patch("os.path.exists")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_load_config_valid(self, mock_yaml_load, mock_open, mock_exists):
        """Test loading valid configuration."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {"face_recognition": {"reference_photos_dir": "./reference_photos"}}

        config = load_config()

        assert config == {"face_recognition": {"reference_photos_dir": "./reference_photos"}}
        mock_exists.assert_called_once_with("config/config.yaml")

    @patch("os.path.exists")
    def test_load_config_missing_file(self, mock_exists):
        """Test handling of missing config file."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            load_config()


class TestGetReferencePhotos:
    """Test get_reference_photos function."""

    @patch("os.path.exists")
    @patch("glob.glob")
    def test_get_reference_photos_found(self, mock_glob, mock_exists):
        """Test finding reference photos successfully."""
        mock_exists.return_value = True
        mock_glob.return_value = ["./reference_photos/photo1.jpg", "./reference_photos/photo2.png"]

        photos = get_reference_photos("./reference_photos", [".jpg", ".png"])

        assert photos == ["./reference_photos/photo1.jpg", "./reference_photos/photo2.png"]
        mock_glob.assert_called()

    @patch("os.path.exists")
    def test_get_reference_photos_missing_directory(self, mock_exists):
        """Test handling of missing reference photos directory."""
        mock_exists.return_value = False

        with pytest.raises(SystemExit):
            get_reference_photos("./missing_dir", [".jpg"])

    @patch("os.path.exists")
    @patch("glob.glob")
    def test_get_reference_photos_no_photos(self, mock_glob, mock_exists):
        """Test handling when no reference photos are found."""
        mock_exists.return_value = True
        mock_glob.return_value = []

        photos = get_reference_photos("./empty_dir", [".jpg"])

        assert photos == []

    @patch("os.path.exists")
    @patch("glob.glob")
    def test_get_reference_photos_filters_system_files(self, mock_glob, mock_exists):
        """Test that system files are filtered out."""
        mock_exists.return_value = True
        mock_glob.return_value = [
            "./reference_photos/.DS_Store",
            "./reference_photos/photo1.jpg",
            "./reference_photos/._hidden.jpg",
            "./reference_photos/photo2.png",
        ]

        photos = get_reference_photos("./reference_photos", [".jpg", ".png"])

        assert photos == ["./reference_photos/photo1.jpg", "./reference_photos/photo2.png"]
        assert "./reference_photos/.DS_Store" not in photos
        assert "./reference_photos/._hidden.jpg" not in photos


class TestTrainFaceModelIntegration:
    """Integration tests for training process."""

    @patch("train_face_model.load_config")
    @patch("train_face_model.get_reference_photos")
    @patch("train_face_model.LocalFaceRecognitionProvider")
    @patch("builtins.print")
    def test_training_successful_encoding(self, mock_print, mock_provider_class, mock_get_photos, mock_load_config):
        """Test successful face encoding generation."""
        # Mock config
        mock_load_config.return_value = {
            "face_recognition": {
                "reference_photos_dir": "./reference_photos",
                "local": {"model": "hog", "encoding_model": "large", "training": {"num_jitters": 50}},
            },
            "processing": {"image_extensions": [".jpg", ".png"]},
        }

        # Mock photos found
        mock_get_photos.return_value = ["photo1.jpg", "photo2.jpg"]

        # Mock provider
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)
        mock_provider.load_reference_photos.return_value = 2  # 2 faces loaded
        mock_provider_class.return_value = mock_provider

        # Should complete without raising SystemExit
        main()

        mock_provider.load_reference_photos.assert_called_once_with(["photo1.jpg", "photo2.jpg"])

    @patch("train_face_model.load_config")
    @patch("train_face_model.get_reference_photos")
    @patch("train_face_model.LocalFaceRecognitionProvider")
    @patch("builtins.print")
    def test_training_no_reference_photos(self, mock_print, mock_provider_class, mock_get_photos, mock_load_config):
        """Test handling when no reference photos are found."""
        mock_load_config.return_value = {
            "face_recognition": {"reference_photos_dir": "./reference_photos"},
            "processing": {"image_extensions": [".jpg"]},
        }

        # No photos found
        mock_get_photos.return_value = []

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_provider_class.assert_not_called()

    @patch("train_face_model.load_config")
    @patch("train_face_model.get_reference_photos")
    @patch("train_face_model.LocalFaceRecognitionProvider")
    @patch("builtins.print")
    def test_training_provider_initialization_failure(
        self, mock_print, mock_provider_class, mock_get_photos, mock_load_config
    ):
        """Test handling of provider initialization failure."""
        mock_load_config.return_value = {
            "face_recognition": {"reference_photos_dir": "./reference_photos", "local": {"model": "hog"}},
            "processing": {"image_extensions": [".jpg"]},
        }

        mock_get_photos.return_value = ["photo1.jpg"]

        # Mock provider initialization failure
        mock_provider_class.side_effect = ImportError("face_recognition not installed")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("train_face_model.load_config")
    @patch("train_face_model.get_reference_photos")
    @patch("train_face_model.LocalFaceRecognitionProvider")
    @patch("builtins.print")
    def test_training_configuration_validation_failure(
        self, mock_print, mock_provider_class, mock_get_photos, mock_load_config
    ):
        """Test handling of configuration validation failure."""
        mock_load_config.return_value = {
            "face_recognition": {"reference_photos_dir": "./reference_photos", "local": {"invalid_config": True}},
            "processing": {"image_extensions": [".jpg"]},
        }

        mock_get_photos.return_value = ["photo1.jpg"]

        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (False, "Invalid configuration")
        mock_provider_class.return_value = mock_provider

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("train_face_model.load_config")
    @patch("train_face_model.get_reference_photos")
    @patch("train_face_model.LocalFaceRecognitionProvider")
    @patch("builtins.print")
    def test_training_load_reference_photos_failure(self, mock_print, mock_provider_class, mock_get_photos, mock_load_config):
        """Test handling of failure during reference photo loading."""
        mock_load_config.return_value = {
            "face_recognition": {"reference_photos_dir": "./reference_photos", "local": {"model": "hog"}},
            "processing": {"image_extensions": [".jpg"]},
        }

        mock_get_photos.return_value = ["photo1.jpg", "photo2.jpg"]

        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)
        mock_provider.load_reference_photos.side_effect = Exception("Corrupted image file")
        mock_provider_class.return_value = mock_provider

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
