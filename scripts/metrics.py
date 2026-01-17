"""
Metrics collection module for tracking AWS Rekognition API usage and costs.

This module provides a lightweight MetricsCollector for gathering:
- API call counts for each Rekognition operation
- Face detection and matching statistics
- Cost estimates based on configured pricing
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class MetricsCollector:
    """
    Collects and aggregates metrics for AWS face recognition operations.

    Tracks:
    - API call counts by operation type
    - Face detection counts (detected, matched, unmatched)
    - Image processing statistics
    - Estimated costs based on pricing configuration
    """

    def __init__(self, pricing_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the metrics collector.

        Args:
            pricing_config: Optional pricing configuration dict with keys:
                - currency: Currency code (e.g., "USD")
                - detect_faces_per_1000: Cost per 1000 DetectFaces calls
                - compare_faces_per_1000: Cost per 1000 CompareFaces calls
                - search_faces_per_1000: Cost per 1000 SearchFacesByImage calls
                - index_faces_per_1000: Cost per 1000 IndexFaces calls
                - list_faces_per_1000: Cost per 1000 ListFaces calls
                - describe_collection_per_1000: Cost per 1000 DescribeCollection calls
                - create_collection_per_1000: Cost per 1000 CreateCollection calls
        """
        self.logger = logging.getLogger(__name__)
        self.pricing_config = pricing_config or {}

        # API call counters
        self.api_calls: Dict[str, int] = {
            "detect_faces": 0,
            "compare_faces": 0,
            "search_faces": 0,
            "index_faces": 0,
            "list_faces": 0,
            "describe_collection": 0,
            "create_collection": 0,
        }

        # Face detection statistics
        self.total_faces_detected = 0
        self.total_faces_matched = 0
        self.total_faces_unmatched = 0

        # Image processing statistics
        self.images_processed = 0
        self.images_with_faces = 0
        self.images_without_faces = 0
        self.images_with_matches = 0
        self.images_skipped = 0
        self.images_errored = 0

        # Per-image aggregates for statistics
        self.faces_per_image: List[int] = []

        # Timing
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def start_collection(self) -> None:
        """Mark the start of metrics collection."""
        self.start_time = datetime.now()

    def end_collection(self) -> None:
        """Mark the end of metrics collection."""
        self.end_time = datetime.now()

    def increment_api_call(self, operation: str, count: int = 1) -> None:
        """
        Increment the counter for a specific API operation.

        Args:
            operation: Operation name (e.g., "detect_faces", "compare_faces")
            count: Number of calls to increment (default: 1)
        """
        if operation in self.api_calls:
            self.api_calls[operation] += count
        else:
            self.logger.warning(f"Unknown API operation: {operation}")

    def record_face_detection(self, num_faces: int, num_matches: int = 0) -> None:
        """
        Record face detection results for an image.

        Args:
            num_faces: Total number of faces detected
            num_matches: Number of faces that matched the reference
        """
        self.total_faces_detected += num_faces
        self.total_faces_matched += num_matches
        self.total_faces_unmatched += num_faces - num_matches
        self.faces_per_image.append(num_faces)

    def record_image_processed(self, has_faces: bool, has_matches: bool) -> None:
        """
        Record that an image was processed.

        Args:
            has_faces: Whether the image contained any faces
            has_matches: Whether the image contained matching faces
        """
        self.images_processed += 1

        if has_faces:
            self.images_with_faces += 1
        else:
            self.images_without_faces += 1

        if has_matches:
            self.images_with_matches += 1

    def record_image_skipped(self) -> None:
        """Record that an image was skipped (e.g., no faces detected)."""
        self.images_skipped += 1

    def record_image_error(self) -> None:
        """Record that an image processing failed."""
        self.images_errored += 1

    def calculate_cost(self) -> Optional[float]:
        """
        Calculate estimated total cost based on API calls and pricing config.

        Returns:
            Total estimated cost, or None if pricing not configured
        """
        if not self.pricing_config:
            return None

        total_cost = 0.0

        # Map API operations to pricing keys
        pricing_map = {
            "detect_faces": "detect_faces_per_1000",
            "compare_faces": "compare_faces_per_1000",
            "search_faces": "search_faces_per_1000",
            "index_faces": "index_faces_per_1000",
            "list_faces": "list_faces_per_1000",
            "describe_collection": "describe_collection_per_1000",
            "create_collection": "create_collection_per_1000",
        }

        for operation, count in self.api_calls.items():
            pricing_key = pricing_map.get(operation)
            if pricing_key and pricing_key in self.pricing_config:
                price_per_1000 = self.pricing_config[pricing_key]
                total_cost += (count / 1000.0) * price_per_1000

        return total_cost

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all collected metrics.

        Returns:
            Dictionary containing all metrics
        """
        summary: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": None,
            "api_calls": self.api_calls.copy(),
            "total_api_calls": sum(self.api_calls.values()),
            "face_statistics": {
                "total_detected": self.total_faces_detected,
                "total_matched": self.total_faces_matched,
                "total_unmatched": self.total_faces_unmatched,
                "max_faces_per_image": max(self.faces_per_image) if self.faces_per_image else 0,
                "avg_faces_per_image": (sum(self.faces_per_image) / len(self.faces_per_image)) if self.faces_per_image else 0,
            },
            "image_statistics": {
                "processed": self.images_processed,
                "with_faces": self.images_with_faces,
                "without_faces": self.images_without_faces,
                "with_matches": self.images_with_matches,
                "skipped": self.images_skipped,
                "errored": self.images_errored,
            },
            "cost_estimate": None,
            "pricing": None,
        }

        # Calculate duration if both start and end times are set
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            summary["duration_seconds"] = duration.total_seconds()

        # Add cost estimate if pricing configured
        cost = self.calculate_cost()
        if cost is not None:
            currency = self.pricing_config.get("currency", "USD")
            summary["cost_estimate"] = {"amount": cost, "currency": currency}
            summary["pricing"] = self.pricing_config.copy()

        return summary

    def log_summary(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Log a human-readable summary of metrics.

        Args:
            logger: Optional logger to use (defaults to module logger)
        """
        log = logger or self.logger
        summary = self.get_summary()

        log.info("=" * 70)
        log.info("AWS Rekognition Metrics Summary")
        log.info("=" * 70)

        # API Calls
        log.info("API Calls:")
        for operation, count in summary["api_calls"].items():
            if count > 0:
                log.info(f"  {operation}: {count}")
        log.info(f"  Total API calls: {summary['total_api_calls']}")
        log.info("")

        # Face Statistics
        face_stats = summary["face_statistics"]
        log.info("Face Statistics:")
        log.info(f"  Total faces detected: {face_stats['total_detected']}")
        log.info(f"  Faces matched: {face_stats['total_matched']}")
        log.info(f"  Faces unmatched: {face_stats['total_unmatched']}")
        log.info(f"  Max faces per image: {face_stats['max_faces_per_image']}")
        log.info(f"  Avg faces per image: {face_stats['avg_faces_per_image']:.2f}")
        log.info("")

        # Image Statistics
        img_stats = summary["image_statistics"]
        log.info("Image Statistics:")
        log.info(f"  Images processed: {img_stats['processed']}")
        log.info(f"  Images with faces: {img_stats['with_faces']}")
        log.info(f"  Images without faces: {img_stats['without_faces']}")
        log.info(f"  Images with matches: {img_stats['with_matches']}")
        log.info(f"  Images skipped: {img_stats['skipped']}")
        log.info(f"  Images errored: {img_stats['errored']}")
        log.info("")

        # Cost Estimate
        if summary["cost_estimate"]:
            cost_info = summary["cost_estimate"]
            log.info(f"Estimated Cost: {cost_info['amount']:.4f} {cost_info['currency']}")
            log.info("(Note: Prices are region-dependent. Update config for accurate estimates)")
        else:
            log.info("Cost Estimate: Not configured")
            log.info("(Add pricing configuration to config.yaml to enable cost estimation)")

        log.info("=" * 70)

    def save_to_file(
        self,
        filepath: str,
        use_timestamp: bool = True,
        create_latest_symlink: bool = True,
    ) -> Optional[str]:
        """
        Save metrics to a JSON file with optional timestamping for historical tracking.

        Args:
            filepath: Path to the output JSON file (e.g., "logs/aws_metrics.json")
            use_timestamp: If True, inserts timestamp before extension
                          (e.g., "logs/aws_metrics_20260117_103045.json")
            create_latest_symlink: If True, creates/updates a "latest" symlink

        Returns:
            The actual filepath where metrics were saved, or None on error
        """
        # Ensure directory exists
        directory = os.path.dirname(os.path.abspath(filepath))
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Generate timestamped filename if requested
        actual_filepath = filepath
        if use_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base, ext = os.path.splitext(filepath)
            actual_filepath = f"{base}_{timestamp}{ext}"

        summary = self.get_summary()

        try:
            with open(actual_filepath, "w") as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Metrics saved to {actual_filepath}")

            # Create/update "latest" symlink for convenience
            if use_timestamp and create_latest_symlink:
                self._create_latest_symlink(filepath, actual_filepath)

            return actual_filepath
        except Exception as e:
            self.logger.error(f"Failed to save metrics to {actual_filepath}: {e}")
            return None

    def _create_latest_symlink(self, base_filepath: str, actual_filepath: str) -> None:
        """
        Create or update a symlink pointing to the latest metrics file.

        Args:
            base_filepath: Original filepath (e.g., "logs/aws_metrics.json")
            actual_filepath: Timestamped filepath that was written
        """
        base, ext = os.path.splitext(base_filepath)
        symlink_path = f"{base}_latest{ext}"

        try:
            # Remove existing symlink if present
            if os.path.islink(symlink_path):
                os.unlink(symlink_path)
            elif os.path.exists(symlink_path):
                # It's a regular file, don't overwrite
                self.logger.warning(f"Cannot create latest symlink: {symlink_path} exists as regular file")
                return

            # Create relative symlink
            actual_filename = os.path.basename(actual_filepath)
            os.symlink(actual_filename, symlink_path)
            self.logger.debug(f"Updated latest symlink: {symlink_path} -> {actual_filename}")
        except OSError as e:
            # Symlinks may not be supported on all platforms
            self.logger.debug(f"Could not create symlink {symlink_path}: {e}")

    def append_to_monthly_costs(self, logs_dir: str = "logs") -> Optional[str]:
        """
        Append this run's cost to a monthly aggregate file.

        Creates or updates a file named aws_costs_YYYY-MM.json with:
        - Individual run entries with timestamp, cost, and stats
        - Running monthly total

        Args:
            logs_dir: Directory for log files (default: "logs")

        Returns:
            Path to the monthly costs file, or None on error
        """
        cost = self.calculate_cost()
        if cost is None:
            self.logger.debug("Skipping monthly cost tracking: pricing not configured")
            return None

        # Ensure directory exists
        os.makedirs(logs_dir, exist_ok=True)

        # Generate filename based on current year-month
        now = datetime.now()
        year_month = now.strftime("%Y-%m")
        filepath = os.path.join(logs_dir, f"aws_costs_{year_month}.json")

        # Load existing data or create new structure
        monthly_data: Dict[str, Any]
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    monthly_data = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"Could not read existing monthly file, creating new: {e}")
                monthly_data = self._create_monthly_structure(year_month)
        else:
            monthly_data = self._create_monthly_structure(year_month)

        # Create run entry
        currency = self.pricing_config.get("currency", "USD")
        run_entry = {
            "timestamp": now.isoformat(),
            "cost": round(cost, 6),
            "api_calls": sum(self.api_calls.values()),
            "api_breakdown": {k: v for k, v in self.api_calls.items() if v > 0},
            "images_processed": self.images_processed,
            "matches_found": self.images_with_matches,
        }

        # Append run and update totals
        monthly_data["runs"].append(run_entry)
        monthly_data["total_cost"] = round(sum(run["cost"] for run in monthly_data["runs"]), 6)
        monthly_data["total_api_calls"] = sum(run["api_calls"] for run in monthly_data["runs"])
        monthly_data["run_count"] = len(monthly_data["runs"])
        monthly_data["last_updated"] = now.isoformat()
        monthly_data["currency"] = currency

        # Save updated data
        try:
            with open(filepath, "w") as f:
                json.dump(monthly_data, f, indent=2)
            self.logger.info(
                f"Monthly costs updated: {filepath} "
                f"(Run: ${cost:.4f}, Month total: ${monthly_data['total_cost']:.4f} {currency})"
            )
            return filepath
        except IOError as e:
            self.logger.error(f"Failed to save monthly costs to {filepath}: {e}")
            return None

    def _create_monthly_structure(self, year_month: str) -> Dict[str, Any]:
        """Create a new monthly cost tracking structure."""
        return {
            "year_month": year_month,
            "currency": self.pricing_config.get("currency", "USD"),
            "total_cost": 0.0,
            "total_api_calls": 0,
            "run_count": 0,
            "last_updated": None,
            "runs": [],
        }
