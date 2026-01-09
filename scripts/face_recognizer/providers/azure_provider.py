"""
Azure Face API face recognition provider.
Uses Azure Cognitive Services Face API for face detection and identification.
"""

import io
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from azure.cognitiveservices.vision.face import FaceClient
    from azure.cognitiveservices.vision.face.models import TrainingStatusType
    from msrest.authentication import CognitiveServicesCredentials

    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

# Default training timeout in seconds (5 minutes)
DEFAULT_TRAINING_TIMEOUT = 300

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.face_recognizer.base_provider import BaseFaceRecognitionProvider, FaceEncoding, FaceMatch  # noqa: E402


class AzureFaceRecognitionProvider(BaseFaceRecognitionProvider):
    """
    Azure Face API face recognition provider.

    Pros:
    - High accuracy
    - Dedicated person/face identification features
    - Good for large-scale face recognition
    - Persistent face data (optional)

    Cons:
    - Requires Azure account and subscription
    - API costs per transaction
    - Data sent to Azure (privacy consideration)
    - Requires internet connection
    - More complex setup (person groups, training)

    Configuration:
    - azure_api_key: Azure Face API subscription key
    - azure_endpoint: Azure Face API endpoint URL
    - person_group_id: Optional person group ID (will be created if not exists)
    - confidence_threshold: Minimum confidence (default: 0.5)
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Azure Face API provider."""
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        if not AZURE_AVAILABLE:
            raise ImportError(
                "azure-cognitiveservices-vision-face library not installed. "
                "Install with: pip install azure-cognitiveservices-vision-face"
            )

        api_key = config.get("azure_api_key")
        endpoint = config.get("azure_endpoint")

        if not api_key or not endpoint:
            raise ValueError("azure_api_key and azure_endpoint are required")

        # Initialize Face client
        self.client = FaceClient(endpoint, CognitiveServicesCredentials(api_key))

        self.person_group_id = config.get("person_group_id", "dropbox-photo-organizer")
        self.confidence_threshold = config.get("confidence_threshold", 0.5)
        self.training_timeout = config.get("training_timeout", DEFAULT_TRAINING_TIMEOUT)
        self.person_id: Optional[str] = None  # Will be created when loading reference photos

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "azure"

    def validate_configuration(self) -> Tuple[bool, Optional[str]]:
        """Validate Azure configuration."""
        if not AZURE_AVAILABLE:
            return False, "azure-cognitiveservices-vision-face library not installed"

        try:
            # Test API call - list person groups
            self.client.person_group.list()
            return True, None
        except Exception as e:
            return False, f"Azure Face API error: {str(e)}"

    def _create_or_get_person_group(self) -> None:
        """Create person group if it doesn't exist."""
        try:
            self.client.person_group.get(self.person_group_id)
            self.logger.info(f"Using existing person group: {self.person_group_id}")
        except Exception as e:
            # Person group doesn't exist, create it
            self.logger.debug(f"Person group not found, creating new one: {e}")
            self.client.person_group.create(
                person_group_id=self.person_group_id,
                name="Dropbox Photo Organizer",
                recognition_model="recognition_04",  # Latest model
            )
            self.logger.info(f"Created new person group: {self.person_group_id}")

    def _create_or_get_person(self, name: str = "Target Person") -> None:
        """Create or get person in the person group."""
        try:
            # List existing persons
            persons = self.client.person_group_person.list(self.person_group_id)
            if persons:
                # Use first person
                self.person_id = persons[0].person_id
                self.logger.info(f"Using existing person: {persons[0].name}")
            else:
                # Create new person
                person = self.client.person_group_person.create(self.person_group_id, name=name)
                self.person_id = person.person_id
                self.logger.info(f"Created new person: {name}")
        except Exception as e:
            self.logger.error(f"Error creating/getting person: {e}")
            raise

    def _add_reference_face(self, photo_path: str) -> bool:
        """Add a single reference face from photo path.

        Args:
            photo_path: Path to the reference photo file

        Returns:
            True if face was added successfully, False otherwise
        """
        if not os.path.exists(photo_path):
            self.logger.warning(f"Reference photo not found: {photo_path}")
            return False

        try:
            with open(photo_path, "rb") as f:
                image_data = f.read()

            # Wrap in BytesIO stream for Azure SDK
            image_stream = io.BytesIO(image_data)

            # Add face to person using latest detection model
            self.client.person_group_person.add_face_from_stream(
                self.person_group_id,
                self.person_id,
                image_stream,
                detection_model="detection_03",
            )

            # Store as FaceEncoding for compatibility (empty encoding, Azure handles storage)
            self.reference_encodings.append(FaceEncoding(encoding=np.array([]), source=photo_path))

            self.logger.info(f"Added reference face from: {photo_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error adding reference photo {photo_path}: {e}")
            return False

    def _train_person_group(self) -> None:
        """Train the person group and wait for completion.

        Raises:
            TimeoutError: If training exceeds configured timeout
            Exception: If training fails
        """
        self.logger.info("Training Azure Face model...")
        self.client.person_group.train(self.person_group_id)

        # Wait for training to complete with timeout
        start_time = time.time()
        while True:
            elapsed = time.time() - start_time
            if elapsed > self.training_timeout:
                raise TimeoutError(
                    f"Training timed out after {self.training_timeout} seconds. "
                    "Increase 'training_timeout' in config or check Azure portal for status."
                )

            training_status = self.client.person_group.get_training_status(self.person_group_id)
            if training_status.status == TrainingStatusType.succeeded:
                self.logger.info(f"Training completed successfully in {elapsed:.1f} seconds")
                break
            elif training_status.status == TrainingStatusType.failed:
                raise Exception(f"Training failed: {training_status.message}")

            time.sleep(1)

    def load_reference_photos(self, photo_paths: List[str]) -> int:
        """
        Load reference photos and train Azure person model.

        Args:
            photo_paths: List of paths to reference photos

        Returns:
            Number of faces successfully added
        """
        # Create or get person group
        self._create_or_get_person_group()

        # Create or get person
        self._create_or_get_person()

        # Add all reference faces
        face_count = sum(1 for photo_path in photo_paths if self._add_reference_face(photo_path))

        if face_count == 0:
            raise Exception("No reference faces could be added")

        # Train the person group
        try:
            self._train_person_group()
        except Exception as e:
            self.logger.error(f"Training error: {e}")
            raise

        return face_count

    def detect_faces(self, image_data: bytes, source: str = "unknown") -> List[FaceEncoding]:
        """
        Detect faces using Azure Face API.

        Args:
            image_data: Raw image bytes
            source: Image source identifier

        Returns:
            List of detected face encodings
        """
        try:
            # Wrap bytes in BytesIO stream for Azure SDK
            image_stream = io.BytesIO(image_data)
            detected_faces = self.client.face.detect_with_stream(
                image_stream,
                detection_model="detection_03",
                recognition_model="recognition_04",
                return_face_id=True,
            )

            face_encodings = []
            for face in detected_faces:
                # Store face_id as string in a numpy array with object dtype
                # This preserves the UUID string for later retrieval
                face_encodings.append(
                    FaceEncoding(
                        encoding=np.array([str(face.face_id)], dtype=object),
                        source=source,
                        confidence=None,
                    )
                )

            return face_encodings

        except Exception as e:
            self.logger.error(f"Error detecting faces in {source}: {e}")
            return []

    def compare_faces(self, face_encoding: FaceEncoding, tolerance: Optional[float] = None) -> FaceMatch:
        """
        Compare face against reference using Azure Face API.

        Args:
            face_encoding: Face encoding (contains face_id as string in encoding array)
            tolerance: Confidence threshold (0-1)

        Returns:
            FaceMatch object
        """
        if tolerance is None:
            tolerance = self.confidence_threshold

        if not self.person_id:
            self.logger.warning("No person_id set - cannot compare faces")
            return FaceMatch(is_match=False, confidence=0.0, distance=1.0)

        try:
            # Extract face_id string from encoding array
            face_id = str(face_encoding.encoding[0])

            results = self.client.face.identify(
                [face_id],
                self.person_group_id,
                confidence_threshold=tolerance,
            )

            if results and results[0].candidates:
                # Check if identified as our target person
                for candidate in results[0].candidates:
                    if str(candidate.person_id) == str(self.person_id):
                        confidence = float(candidate.confidence)

                        return FaceMatch(
                            is_match=True,
                            confidence=confidence,
                            distance=1.0 - confidence,
                            matched_encoding=None,
                        )

            return FaceMatch(is_match=False, confidence=0.0, distance=1.0)

        except Exception as e:
            self.logger.error(f"Error comparing faces: {e}")
            return FaceMatch(is_match=False, confidence=0.0, distance=1.0)
