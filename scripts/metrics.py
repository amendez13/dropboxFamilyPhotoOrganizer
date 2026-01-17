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

    def save_to_file(self, filepath: str) -> None:
        """
        Save metrics to a JSON file.

        Args:
            filepath: Path to the output JSON file
        """
        # Ensure directory exists
        directory = os.path.dirname(os.path.abspath(filepath))
        if directory:
            os.makedirs(directory, exist_ok=True)

        summary = self.get_summary()

        try:
            with open(filepath, "w") as f:
                json.dump(summary, f, indent=2)
            self.logger.info(f"Metrics saved to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics to {filepath}: {e}")
