"""
Unit tests for metrics collection module.
"""

import json
import os
import tempfile
from unittest.mock import MagicMock

from scripts.metrics import MetricsCollector


class TestMetricsCollector:
    """Test MetricsCollector functionality."""

    def test_initialization_without_pricing(self):
        """Test initialization without pricing configuration."""
        collector = MetricsCollector()

        assert collector.pricing_config == {}
        assert collector.api_calls == {
            "detect_faces": 0,
            "compare_faces": 0,
            "search_faces": 0,
            "index_faces": 0,
            "list_faces": 0,
            "describe_collection": 0,
            "create_collection": 0,
        }
        assert collector.total_faces_detected == 0
        assert collector.total_faces_matched == 0
        assert collector.images_processed == 0

    def test_initialization_with_pricing(self):
        """Test initialization with pricing configuration."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            "compare_faces_per_1000": 1.0,
        }
        collector = MetricsCollector(pricing_config=pricing)

        assert collector.pricing_config == pricing

    def test_increment_api_call(self):
        """Test incrementing API call counters."""
        collector = MetricsCollector()

        collector.increment_api_call("detect_faces")
        assert collector.api_calls["detect_faces"] == 1

        collector.increment_api_call("detect_faces", count=5)
        assert collector.api_calls["detect_faces"] == 6

        collector.increment_api_call("compare_faces", count=10)
        assert collector.api_calls["compare_faces"] == 10

    def test_increment_unknown_operation(self):
        """Test incrementing unknown API operation logs warning."""
        collector = MetricsCollector()

        # Should not raise error, but should log warning
        collector.increment_api_call("unknown_operation")

        # Known operations should still work
        collector.increment_api_call("detect_faces")
        assert collector.api_calls["detect_faces"] == 1

    def test_record_face_detection(self):
        """Test recording face detection results."""
        collector = MetricsCollector()

        collector.record_face_detection(num_faces=3, num_matches=1)

        assert collector.total_faces_detected == 3
        assert collector.total_faces_matched == 1
        assert collector.total_faces_unmatched == 2
        assert collector.faces_per_image == [3]

        collector.record_face_detection(num_faces=5, num_matches=2)

        assert collector.total_faces_detected == 8
        assert collector.total_faces_matched == 3
        assert collector.total_faces_unmatched == 5
        assert collector.faces_per_image == [3, 5]

    def test_record_image_processed(self):
        """Test recording image processing statistics."""
        collector = MetricsCollector()

        # Image with faces and matches
        collector.record_image_processed(has_faces=True, has_matches=True)
        assert collector.images_processed == 1
        assert collector.images_with_faces == 1
        assert collector.images_with_matches == 1

        # Image with faces but no matches
        collector.record_image_processed(has_faces=True, has_matches=False)
        assert collector.images_processed == 2
        assert collector.images_with_faces == 2
        assert collector.images_with_matches == 1

        # Image without faces
        collector.record_image_processed(has_faces=False, has_matches=False)
        assert collector.images_processed == 3
        assert collector.images_with_faces == 2
        assert collector.images_without_faces == 1

    def test_record_image_skipped_and_error(self):
        """Test recording skipped and errored images."""
        collector = MetricsCollector()

        collector.record_image_skipped()
        assert collector.images_skipped == 1

        collector.record_image_error()
        assert collector.images_errored == 1

    def test_calculate_cost_without_pricing(self):
        """Test cost calculation without pricing configuration."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=100)

        cost = collector.calculate_cost()
        assert cost is None

    def test_calculate_cost_with_pricing(self):
        """Test cost calculation with pricing configuration."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            "compare_faces_per_1000": 1.0,
            "search_faces_per_1000": 6.0,
        }
        collector = MetricsCollector(pricing_config=pricing)

        # 100 detect_faces calls = 100/1000 * 1.0 = $0.10
        collector.increment_api_call("detect_faces", count=100)

        # 50 compare_faces calls = 50/1000 * 1.0 = $0.05
        collector.increment_api_call("compare_faces", count=50)

        # 10 search_faces calls = 10/1000 * 6.0 = $0.06
        collector.increment_api_call("search_faces", count=10)

        cost = collector.calculate_cost()
        assert cost is not None
        assert abs(cost - 0.21) < 0.001  # $0.10 + $0.05 + $0.06 = $0.21

    def test_calculate_cost_partial_pricing(self):
        """Test cost calculation with partial pricing configuration."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            # compare_faces_per_1000 not configured
        }
        collector = MetricsCollector(pricing_config=pricing)

        collector.increment_api_call("detect_faces", count=100)
        collector.increment_api_call("compare_faces", count=50)  # Should be ignored

        cost = collector.calculate_cost()
        assert cost is not None
        assert abs(cost - 0.10) < 0.001  # Only detect_faces counted

    def test_get_summary_basic(self):
        """Test getting basic metrics summary."""
        collector = MetricsCollector()

        collector.increment_api_call("detect_faces", count=10)
        collector.increment_api_call("compare_faces", count=5)
        collector.record_face_detection(num_faces=3, num_matches=1)
        collector.record_image_processed(has_faces=True, has_matches=True)

        summary = collector.get_summary()

        assert summary["api_calls"]["detect_faces"] == 10
        assert summary["api_calls"]["compare_faces"] == 5
        assert summary["total_api_calls"] == 15
        assert summary["face_statistics"]["total_detected"] == 3
        assert summary["face_statistics"]["total_matched"] == 1
        assert summary["face_statistics"]["max_faces_per_image"] == 3
        assert summary["image_statistics"]["processed"] == 1
        assert summary["cost_estimate"] is None

    def test_get_summary_with_pricing(self):
        """Test getting metrics summary with pricing."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)

        collector.increment_api_call("detect_faces", count=100)

        summary = collector.get_summary()

        assert summary["cost_estimate"] is not None
        assert summary["cost_estimate"]["currency"] == "USD"
        assert abs(summary["cost_estimate"]["amount"] - 0.10) < 0.001
        assert summary["pricing"] == pricing

    def test_get_summary_with_timing(self):
        """Test getting metrics summary with timing information."""
        collector = MetricsCollector()

        collector.start_collection()
        collector.end_collection()

        summary = collector.get_summary()

        assert summary["duration_seconds"] is not None
        assert summary["duration_seconds"] >= 0

    def test_avg_faces_per_image(self):
        """Test average faces per image calculation."""
        collector = MetricsCollector()

        collector.record_face_detection(num_faces=2, num_matches=1)
        collector.record_face_detection(num_faces=4, num_matches=2)
        collector.record_face_detection(num_faces=6, num_matches=1)

        summary = collector.get_summary()

        # Average: (2 + 4 + 6) / 3 = 4.0
        assert abs(summary["face_statistics"]["avg_faces_per_image"] - 4.0) < 0.001
        assert summary["face_statistics"]["max_faces_per_image"] == 6

    def test_avg_faces_per_image_empty(self):
        """Test average faces per image when no images processed."""
        collector = MetricsCollector()

        summary = collector.get_summary()

        assert summary["face_statistics"]["avg_faces_per_image"] == 0
        assert summary["face_statistics"]["max_faces_per_image"] == 0

    def test_save_to_file_with_timestamp(self):
        """Test saving metrics to JSON file with timestamp."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=10)
        collector.record_face_detection(num_faces=3, num_matches=1)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")
            actual_path = collector.save_to_file(filepath, use_timestamp=True)

            # Should return the actual path with timestamp
            assert actual_path is not None
            assert actual_path != filepath
            assert "metrics_" in actual_path
            assert actual_path.endswith(".json")
            assert os.path.exists(actual_path)

            # Check symlink was created
            symlink_path = os.path.join(tmpdir, "metrics_latest.json")
            assert os.path.islink(symlink_path)

            with open(actual_path, "r") as f:
                data = json.load(f)

            assert data["api_calls"]["detect_faces"] == 10
            assert data["face_statistics"]["total_detected"] == 3

    def test_save_to_file_without_timestamp(self):
        """Test saving metrics without timestamp (overwrite mode)."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")
            actual_path = collector.save_to_file(filepath, use_timestamp=False)

            # Should return exact filepath
            assert actual_path == filepath
            assert os.path.exists(filepath)

    def test_save_to_file_creates_directory(self):
        """Test that save_to_file creates directory if it doesn't exist."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "logs", "metrics.json")
            actual_path = collector.save_to_file(filepath, use_timestamp=False)

            assert actual_path is not None
            assert os.path.exists(actual_path)

    def test_save_to_file_historical_tracking(self):
        """Test that multiple saves create separate timestamped files."""
        import time

        collector1 = MetricsCollector()
        collector1.increment_api_call("detect_faces", count=5)

        collector2 = MetricsCollector()
        collector2.increment_api_call("detect_faces", count=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")

            path1 = collector1.save_to_file(filepath, use_timestamp=True)
            time.sleep(1.1)  # Ensure different timestamp
            path2 = collector2.save_to_file(filepath, use_timestamp=True)

            # Both files should exist with different names
            assert path1 != path2
            assert os.path.exists(path1)
            assert os.path.exists(path2)

            # Latest symlink should point to second file
            symlink_path = os.path.join(tmpdir, "metrics_latest.json")
            assert os.path.islink(symlink_path)
            assert os.readlink(symlink_path) == os.path.basename(path2)

    def test_save_to_file_no_symlink(self):
        """Test saving without creating symlink."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")
            actual_path = collector.save_to_file(filepath, use_timestamp=True, create_latest_symlink=False)

            assert actual_path is not None
            assert os.path.exists(actual_path)

            # No symlink should be created
            symlink_path = os.path.join(tmpdir, "metrics_latest.json")
            assert not os.path.exists(symlink_path)

    def test_log_summary(self):
        """Test logging metrics summary."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)

        collector.increment_api_call("detect_faces", count=100)
        collector.record_face_detection(num_faces=5, num_matches=2)
        collector.record_image_processed(has_faces=True, has_matches=True)

        # Create a mock logger
        mock_logger = MagicMock()

        # Should not raise any errors
        collector.log_summary(logger=mock_logger)

        # Verify logger was called
        assert mock_logger.info.called

    def test_log_summary_without_pricing(self):
        """Test logging metrics summary without pricing configuration."""
        collector = MetricsCollector()  # No pricing config

        collector.increment_api_call("detect_faces", count=100)
        collector.record_face_detection(num_faces=5, num_matches=2)

        mock_logger = MagicMock()
        collector.log_summary(logger=mock_logger)

        # Should log "Cost Estimate: Not configured"
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Not configured" in str(call) for call in log_calls)

    def test_complete_workflow_compare_faces_mode(self):
        """Test complete workflow for CompareFaces mode."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            "compare_faces_per_1000": 1.0,
        }
        collector = MetricsCollector(pricing_config=pricing)

        collector.start_collection()

        # Simulate processing 10 images with CompareFaces
        for i in range(10):
            # Each image: 1 DetectFaces call + 1 CompareFaces call
            collector.increment_api_call("detect_faces")
            collector.increment_api_call("compare_faces")

            # Simulate some having faces, some matching
            has_faces = i % 3 != 0  # 2/3 have faces
            has_matches = i % 5 == 0  # 1/5 have matches

            if has_faces:
                num_matches = 1 if has_matches else 0
                collector.record_face_detection(num_faces=2, num_matches=num_matches)
                collector.record_image_processed(has_faces=True, has_matches=has_matches)
            else:
                collector.record_image_processed(has_faces=False, has_matches=False)

        collector.end_collection()

        summary = collector.get_summary()

        assert summary["api_calls"]["detect_faces"] == 10
        assert summary["api_calls"]["compare_faces"] == 10
        assert summary["total_api_calls"] == 20
        assert summary["image_statistics"]["processed"] == 10

        # Cost: (10/1000 * 1.0) + (10/1000 * 1.0) = $0.02
        assert summary["cost_estimate"] is not None
        assert abs(summary["cost_estimate"]["amount"] - 0.02) < 0.001

    def test_complete_workflow_collection_mode(self):
        """Test complete workflow for Collection mode."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            "search_faces_per_1000": 6.0,
            "index_faces_per_1000": 1.0,
            "describe_collection_per_1000": 0.0,
            "create_collection_per_1000": 0.0,
        }
        collector = MetricsCollector(pricing_config=pricing)

        collector.start_collection()

        # Setup: Create collection and index reference faces
        collector.increment_api_call("describe_collection")
        collector.increment_api_call("create_collection")
        collector.increment_api_call("index_faces", count=3)  # 3 reference photos

        # Process images using SearchFacesByImage
        for i in range(10):
            # Each image: 1 DetectFaces call + 1 SearchFacesByImage call
            collector.increment_api_call("detect_faces")
            collector.increment_api_call("search_faces")

            has_faces = i % 3 != 0
            has_matches = i % 4 == 0

            if has_faces:
                num_matches = 1 if has_matches else 0
                collector.record_face_detection(num_faces=2, num_matches=num_matches)
                collector.record_image_processed(has_faces=True, has_matches=has_matches)
            else:
                collector.record_image_processed(has_faces=False, has_matches=False)

        collector.end_collection()

        summary = collector.get_summary()

        assert summary["api_calls"]["describe_collection"] == 1
        assert summary["api_calls"]["create_collection"] == 1
        assert summary["api_calls"]["index_faces"] == 3
        assert summary["api_calls"]["detect_faces"] == 10
        assert summary["api_calls"]["search_faces"] == 10

        # Cost calculation:
        # describe_collection: 1/1000 * 0.0 = $0.00
        # create_collection: 1/1000 * 0.0 = $0.00
        # index_faces: 3/1000 * 1.0 = $0.003
        # detect_faces: 10/1000 * 1.0 = $0.01
        # search_faces: 10/1000 * 6.0 = $0.06
        # Total: $0.073
        assert summary["cost_estimate"] is not None
        assert abs(summary["cost_estimate"]["amount"] - 0.073) < 0.001

    def test_append_to_monthly_costs_creates_new_file(self):
        """Test that append_to_monthly_costs creates a new monthly file."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)

        collector.increment_api_call("detect_faces", count=100)
        collector.record_image_processed(has_faces=True, has_matches=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = collector.append_to_monthly_costs(logs_dir=tmpdir)

            assert filepath is not None
            assert os.path.exists(filepath)
            assert "aws_costs_" in filepath
            assert filepath.endswith(".json")

            with open(filepath, "r") as f:
                data = json.load(f)

            assert data["run_count"] == 1
            assert data["currency"] == "USD"
            assert abs(data["total_cost"] - 0.1) < 0.001
            assert data["total_api_calls"] == 100
            assert len(data["runs"]) == 1
            assert data["runs"][0]["images_processed"] == 1
            assert data["runs"][0]["matches_found"] == 1

    def test_append_to_monthly_costs_appends_to_existing(self):
        """Test that append_to_monthly_costs appends to existing monthly file."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}

        with tempfile.TemporaryDirectory() as tmpdir:
            # First run
            collector1 = MetricsCollector(pricing_config=pricing)
            collector1.increment_api_call("detect_faces", count=100)
            collector1.record_image_processed(has_faces=True, has_matches=True)
            filepath1 = collector1.append_to_monthly_costs(logs_dir=tmpdir)

            # Second run
            collector2 = MetricsCollector(pricing_config=pricing)
            collector2.increment_api_call("detect_faces", count=50)
            collector2.record_image_processed(has_faces=True, has_matches=False)
            filepath2 = collector2.append_to_monthly_costs(logs_dir=tmpdir)

            # Should be same file
            assert filepath1 == filepath2

            with open(filepath2, "r") as f:
                data = json.load(f)

            assert data["run_count"] == 2
            assert abs(data["total_cost"] - 0.15) < 0.001  # $0.10 + $0.05
            assert data["total_api_calls"] == 150  # 100 + 50
            assert len(data["runs"]) == 2
            assert data["runs"][0]["cost"] == 0.1
            assert data["runs"][1]["cost"] == 0.05

    def test_append_to_monthly_costs_without_pricing(self):
        """Test that append_to_monthly_costs returns None without pricing."""
        collector = MetricsCollector()  # No pricing config
        collector.increment_api_call("detect_faces", count=100)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = collector.append_to_monthly_costs(logs_dir=tmpdir)

            assert filepath is None
            # No file should be created
            assert len(os.listdir(tmpdir)) == 0

    def test_append_to_monthly_costs_handles_corrupted_file(self):
        """Test that append_to_monthly_costs handles corrupted JSON gracefully."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)
        collector.increment_api_call("detect_faces", count=100)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a corrupted file
            from datetime import datetime

            year_month = datetime.now().strftime("%Y-%m")
            corrupted_path = os.path.join(tmpdir, f"aws_costs_{year_month}.json")
            with open(corrupted_path, "w") as f:
                f.write("{ invalid json }")

            # Should still work, creating fresh structure
            filepath = collector.append_to_monthly_costs(logs_dir=tmpdir)

            assert filepath is not None
            with open(filepath, "r") as f:
                data = json.load(f)

            assert data["run_count"] == 1
            assert len(data["runs"]) == 1

    def test_append_to_monthly_costs_api_breakdown(self):
        """Test that API breakdown is correctly recorded in monthly costs."""
        pricing = {
            "currency": "USD",
            "detect_faces_per_1000": 1.0,
            "search_faces_per_1000": 1.0,
        }
        collector = MetricsCollector(pricing_config=pricing)

        collector.increment_api_call("detect_faces", count=23)
        collector.increment_api_call("search_faces", count=17)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = collector.append_to_monthly_costs(logs_dir=tmpdir)

            with open(filepath, "r") as f:
                data = json.load(f)

            run = data["runs"][0]
            assert run["api_calls"] == 40
            assert run["api_breakdown"]["detect_faces"] == 23
            assert run["api_breakdown"]["search_faces"] == 17
            # Zero-count operations should not be included
            assert "compare_faces" not in run["api_breakdown"]

    def test_append_to_monthly_costs_creates_directory(self):
        """Test that append_to_monthly_costs creates logs directory if missing."""
        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)
        collector.increment_api_call("detect_faces", count=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            logs_dir = os.path.join(tmpdir, "nested", "logs")
            filepath = collector.append_to_monthly_costs(logs_dir=logs_dir)

            assert filepath is not None
            assert os.path.exists(filepath)
            assert os.path.isdir(logs_dir)

    def test_save_to_file_returns_none_on_write_error(self):
        """Test that save_to_file returns None when write fails."""
        from unittest.mock import patch

        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")

            # Mock open to raise an exception during write
            with patch("builtins.open", side_effect=PermissionError("Mock permission error")):
                result = collector.save_to_file(filepath, use_timestamp=False)

            assert result is None

    def test_symlink_not_created_when_regular_file_exists(self):
        """Test that symlink is not created if a regular file with that name exists."""
        collector = MetricsCollector()
        collector.increment_api_call("detect_faces", count=5)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "metrics.json")
            symlink_path = os.path.join(tmpdir, "metrics_latest.json")

            # Create a regular file where the symlink would go
            with open(symlink_path, "w") as f:
                f.write("existing file")

            # Save metrics - should not overwrite the regular file
            actual_path = collector.save_to_file(filepath, use_timestamp=True)

            assert actual_path is not None
            # The "symlink" should still be a regular file, not a symlink
            assert not os.path.islink(symlink_path)
            # And should still contain original content
            with open(symlink_path, "r") as f:
                assert f.read() == "existing file"

    def test_append_to_monthly_costs_handles_write_error(self):
        """Test that append_to_monthly_costs handles write errors gracefully."""
        from unittest.mock import patch

        pricing = {"currency": "USD", "detect_faces_per_1000": 1.0}
        collector = MetricsCollector(pricing_config=pricing)
        collector.increment_api_call("detect_faces", count=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock open to raise IOError on write
            with patch("builtins.open", side_effect=IOError("Mock write error")):
                result = collector.append_to_monthly_costs(logs_dir=tmpdir)

            # Should return None on error
            assert result is None
