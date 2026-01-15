"""
AWS Rekognition face recognition provider.
Uses AWS Rekognition for face detection and comparison.
"""

import base64
import logging
import os
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

import numpy as np

try:
    import boto3
    from botocore.exceptions import ClientError

    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

if TYPE_CHECKING:
    from PIL import Image as PilImage

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds

AWS_MAX_IMAGE_BYTES = 5 * 1024 * 1024
AWS_MAX_IMAGE_DIMENSION = 1600
AWS_JPEG_QUALITY_STEPS = (85, 80, 75, 70, 65)

_VALIDATION_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAAvElEQVR4nO3QQQkAMAzAwPo3vYq4xyjkFI"
    "TMC5nfAdc1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1"
    "EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1ED"
    "UQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRA1EDUQNRAtkfOhzns52jEAAAAASUVORK5CYII="
)

T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Handles transient failures like throttling and service errors.
    AWS-specific retryable error codes:
    - ThrottlingException: Rate limit exceeded
    - ProvisionedThroughputExceededException: Throughput exceeded
    - ServiceUnavailableException: Temporary service issue
    - InternalServerError: AWS internal error

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        retryable_exceptions: Tuple of exception types to retry on
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            logger = logging.getLogger(__name__)
            last_exception: Optional[BaseException] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    # Check if it's a retryable AWS error
                    is_retryable = False
                    error_str = str(e).lower()

                    # AWS Rekognition specific error codes
                    if isinstance(e, ClientError):
                        error_code = e.response.get("Error", {}).get("Code", "")
                        is_retryable = error_code in [
                            "ThrottlingException",
                            "ProvisionedThroughputExceededException",
                            "ServiceUnavailableException",
                            "InternalServerError",
                        ]
                    else:
                        # Check for retryable patterns in error message
                        is_retryable = any(
                            pattern in error_str
                            for pattern in [
                                "throttl",
                                "rate limit",
                                "timeout",
                                "connection",
                                "temporary",
                                "service unavailable",
                            ]
                        )

                    if attempt < max_retries and is_retryable:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"Retryable error in {func.__name__} (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        # Non-retryable error or max retries exceeded
                        raise

            # Should not reach here, but raise last exception if we do
            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected state in retry logic")

        return wrapper

    return decorator


import sys  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.face_recognizer.base_provider import BaseFaceRecognitionProvider, FaceEncoding, FaceMatch  # noqa: E402


class AWSFaceRecognitionProvider(BaseFaceRecognitionProvider):
    """
    AWS Rekognition face recognition provider.

    Pros:
    - High accuracy
    - Fast processing
    - Scalable for large libraries
    - No local setup/dependencies

    Cons:
    - Requires AWS account and credentials
    - API costs per image
    - Data sent to AWS (privacy consideration)
    - Requires internet connection

    Configuration:
    - aws_access_key_id: AWS access key (or use AWS CLI config)
    - aws_secret_access_key: AWS secret key (or use AWS CLI config)
    - aws_region: AWS region (default: us-east-1)
    - similarity_threshold: Minimum similarity percentage (default: 80)
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize AWS Rekognition provider."""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        if not AWS_AVAILABLE:
            raise ImportError("boto3 library not installed. " "Install with: pip install boto3")

        # Initialize AWS Rekognition client
        aws_config = {}
        if config.get("aws_access_key_id"):
            aws_config["aws_access_key_id"] = config["aws_access_key_id"]
        if config.get("aws_secret_access_key"):
            aws_config["aws_secret_access_key"] = config["aws_secret_access_key"]
        if config.get("aws_region"):
            aws_config["region_name"] = config.get("aws_region", "us-east-1")

        try:
            self.client = boto3.client("rekognition", **aws_config)
        except Exception as e:
            raise Exception(f"Failed to initialize AWS Rekognition client: {e}")

        self.similarity_threshold = config.get("similarity_threshold", 80.0)

        # AWS Rekognition doesn't use encodings like dlib
        # We store the reference image bytes for comparison
        self.reference_images: List[bytes] = []

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "aws"

    def validate_configuration(self) -> Tuple[bool, Optional[str]]:
        """Validate AWS configuration."""
        if not AWS_AVAILABLE:
            return False, "boto3 library not installed"

        try:
            image_bytes = base64.b64decode(_VALIDATION_IMAGE_BASE64)
            self.client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["DEFAULT"])
            return True, None
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in {"InvalidImageFormatException", "InvalidParameterException"}:
                # Image validation issues still confirm credentials are usable.
                return True, None
            return False, f"AWS authentication failed: {str(e)}"
        except Exception as e:
            return False, f"AWS configuration error: {str(e)}"

    def load_reference_photos(self, photo_paths: List[str]) -> int:
        """
        Load reference photos.

        AWS Rekognition compares images directly, so we store the image bytes.

        Args:
            photo_paths: List of paths to reference photos

        Returns:
            Number of reference photos loaded
        """
        self.reference_images = []

        for photo_path in photo_paths:
            if not os.path.exists(photo_path):
                self.logger.warning(f"Reference photo not found: {photo_path}")
                continue

            try:
                with open(photo_path, "rb") as f:
                    image_bytes = f.read()

                image_bytes = self._ensure_max_image_size(image_bytes, photo_path)
                if len(image_bytes) > AWS_MAX_IMAGE_BYTES:
                    self.logger.error(f"Unable to resize reference photo under 5MB, skipping: {photo_path}")
                    continue

                # Verify image has faces with retry support
                response = self._verify_reference_photo_with_retry(image_bytes)
                face_details = response.get("FaceDetails", [])

                if not face_details:
                    self.logger.warning(f"No faces found in reference photo: {photo_path}")
                    continue

                if len(face_details) > 1:
                    self.logger.warning(f"Multiple faces found in reference photo (AWS requires exactly one): {photo_path}")
                    continue

                self.reference_images.append(image_bytes)

                # Store as FaceEncoding for compatibility (encoding is None for AWS)
                self.reference_encodings.append(
                    FaceEncoding(encoding=np.array([]), source=photo_path, confidence=None)  # Placeholder
                )

                self.logger.info(f"Loaded reference photo: {photo_path}")

            except Exception as e:
                self.logger.error(f"Error loading reference photo {photo_path}: {e}")

        if len(self.reference_images) == 0:
            raise Exception("No reference photos could be loaded")

        self.logger.info(f"Loaded {len(self.reference_images)} reference photo(s)")
        return len(self.reference_images)

    @retry_with_backoff(max_retries=DEFAULT_MAX_RETRIES)
    def _verify_reference_photo_with_retry(self, image_bytes: bytes) -> Dict[str, Any]:
        """Internal method for verifying reference photos with retry support."""
        response: Dict[str, Any] = self.client.detect_faces(Image={"Bytes": image_bytes}, Attributes=["DEFAULT"])
        return response

    def detect_faces(self, image_data: bytes, source: str = "unknown") -> List[FaceEncoding]:
        """
        Detect faces using AWS Rekognition.

        Args:
            image_data: Raw image bytes
            source: Image source identifier

        Returns:
            List of detected face encodings (empty encodings for AWS)
        """
        try:
            face_encodings = self._detect_faces_with_retry(image_data, source)
            return face_encodings
        except Exception as e:
            self.logger.error(f"Error detecting faces in {source}: {e}")
            return []

    @retry_with_backoff(max_retries=DEFAULT_MAX_RETRIES)
    def _detect_faces_with_retry(self, image_data: bytes, source: str) -> List[FaceEncoding]:
        """Internal method for face detection with retry support."""
        response = self.client.detect_faces(Image={"Bytes": image_data}, Attributes=["DEFAULT"])

        face_encodings = []
        for face_detail in response["FaceDetails"]:
            # Extract confidence
            confidence = face_detail["Confidence"]

            # Create FaceEncoding (encoding array is empty for AWS)
            face_encodings.append(
                FaceEncoding(
                    encoding=np.array([]),  # AWS doesn't provide encodings
                    source=source,
                    confidence=confidence / 100.0,  # Convert to 0-1 range
                    bounding_box=None,  # AWS uses different format
                )
            )

        return face_encodings

    def compare_faces(self, face_encoding: FaceEncoding, tolerance: Optional[float] = None) -> FaceMatch:
        """
        Compare face against reference photos using AWS Rekognition.

        Note: This method is not typically used with AWS provider.
        Use find_matches_in_image instead for better performance.

        Args:
            face_encoding: Face encoding (contains source image)
            tolerance: Similarity threshold (0-100, default from config)

        Returns:
            FaceMatch object
        """
        # For AWS, we need the full image, not just encoding
        # This is a limitation of the AWS API
        return FaceMatch(is_match=False, confidence=0.0, distance=1.0)

    def find_matches_in_image(
        self, image_data: bytes, source: str = "unknown", tolerance: Optional[float] = None
    ) -> Tuple[List[FaceMatch], int]:
        """
        Find matches in image using AWS Rekognition's compare_faces API.

        This is more efficient than detect + compare for AWS.

        Args:
            image_data: Raw image bytes
            source: Image source identifier
            tolerance: Similarity threshold percentage (0-100)

        Returns:
            Tuple of (list of matches, total faces detected)
        """
        if tolerance is None:
            tolerance = self.similarity_threshold

        image_data = self._ensure_max_image_size(image_data, source)
        if len(image_data) > AWS_MAX_IMAGE_BYTES:
            self.logger.error(f"Unable to resize target image under 5MB, skipping: {source}")
            return [], 0

        if not self._precheck_target_faces(image_data, source):
            return [], 0

        matches: List[FaceMatch] = []
        total_faces = 0

        # Compare against each reference image
        for ref_image in self.reference_images:
            try:
                response = self._compare_faces_with_retry(ref_image, image_data, tolerance)

                # Count all faces in target image
                total_faces = max(total_faces, self._count_faces_in_response(response))

                # Process matches
                self._append_matches_from_response(response, matches)

            except ClientError as e:
                error = e.response.get("Error", {})
                code = error.get("Code", "Unknown")
                message = error.get("Message", str(e))
                self.logger.error(f"Error comparing faces for {source}: {code}: {message}")
            except Exception as e:
                self.logger.error(f"Error comparing faces for {source}: {e}")

        # Remove duplicates if same face matched multiple reference images
        unique_matches = matches[:1] if matches else []  # Take best match

        return unique_matches, total_faces

    @retry_with_backoff(max_retries=DEFAULT_MAX_RETRIES)
    def _compare_faces_with_retry(self, ref_image: bytes, image_data: bytes, tolerance: float) -> Dict[str, Any]:
        """Internal method for compare_faces API call with retry support."""
        response: Dict[str, Any] = self.client.compare_faces(
            SourceImage={"Bytes": ref_image}, TargetImage={"Bytes": image_data}, SimilarityThreshold=tolerance
        )
        return response

    def _ensure_max_image_size(self, image_bytes: bytes, source: str) -> bytes:
        if len(image_bytes) <= AWS_MAX_IMAGE_BYTES:
            return image_bytes

        image = self._load_image_for_resize(image_bytes, source)
        if image is None:
            return image_bytes

        return self._resize_image_bytes(image, source, image_bytes)

    def _precheck_target_faces(self, image_data: bytes, source: str) -> bool:
        try:
            # Avoid CompareFaces errors when the target has no detectable faces.
            precheck_faces = self._detect_faces_with_retry(image_data, source)
            if not precheck_faces:
                self.logger.info(f"No faces detected in target image, skipping: {source}")
                return False
        except Exception as e:
            self.logger.error(f"Error detecting faces for {source}: {e}")
            return False
        return True

    def _count_faces_in_response(self, response: Dict[str, Any]) -> int:
        return len(response.get("UnmatchedFaces", [])) + len(response.get("FaceMatches", []))

    def _append_matches_from_response(self, response: Dict[str, Any], matches: List[FaceMatch]) -> None:
        for match in response.get("FaceMatches", []):
            similarity = match["Similarity"]
            confidence = similarity / 100.0

            matches.append(
                FaceMatch(
                    is_match=True,
                    confidence=confidence,
                    distance=1.0 - confidence,  # Convert similarity to distance
                    matched_encoding=None,
                )
            )

    def _load_image_for_resize(self, image_bytes: bytes, source: str) -> Optional["PilImage.Image"]:
        try:
            from io import BytesIO

            from PIL import Image, ImageOps
        except Exception as e:
            self.logger.error(f"Unable to resize image without Pillow for {source}: {e}")
            return None

        try:
            image: PilImage.Image = Image.open(BytesIO(image_bytes))
            image = ImageOps.exif_transpose(image)
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            return image
        except Exception as e:
            self.logger.error(f"Unable to read image for resizing: {source}: {e}")
            return None

    def _resize_image_bytes(self, image: "PilImage.Image", source: str, fallback_bytes: bytes) -> bytes:
        from io import BytesIO

        from PIL import Image

        max_dim = AWS_MAX_IMAGE_DIMENSION
        smallest = fallback_bytes

        resample = getattr(Image, "Resampling", Image).LANCZOS

        while True:
            working = image.copy()
            working.thumbnail((max_dim, max_dim), resample)

            for quality in AWS_JPEG_QUALITY_STEPS:
                buffer = BytesIO()
                working.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
                data = buffer.getvalue()

                if len(data) <= AWS_MAX_IMAGE_BYTES:
                    self.logger.warning(f"Resized image to fit AWS 5MB limit: {source}")
                    return data

                if len(data) < len(smallest):
                    smallest = data

            if max_dim <= 300:
                self.logger.warning(f"Unable to reach 5MB limit, using smallest resized image: {source}")
                return smallest

            max_dim = int(max_dim * 0.85)
