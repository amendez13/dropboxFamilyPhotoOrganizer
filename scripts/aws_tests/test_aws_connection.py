"""Small script to verify AWS Rekognition configuration and credentials.

Run from project root:
    source venv/bin/activate
    python scripts/aws_tests/test_aws_connection.py

This follows the example in docs/AWS_FACE_RECOGNITION_SETUP.md
"""

import logging
import os
import sys

import yaml

# Ensure project root is on sys.path so scripts package can be imported
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider
except Exception as e:
    print(f"✗ Could not import AWS provider: {e}")
    sys.exit(2)


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    if not os.path.exists(config_path):
        print(f"✗ Config file not found at {config_path}")
        sys.exit(2)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    aws_config = config.get("face_recognition", {}).get("aws", {})

    try:
        provider = AWSFaceRecognitionProvider(aws_config)
        print("✓ AWS Rekognition client initialized")
    except Exception as e:
        print(f"✗ Failed to initialize AWS provider: {e}")
        sys.exit(1)

    try:
        is_valid, error = provider.validate_configuration()
        if is_valid:
            print("✓ AWS credentials/configuration are valid")
            sys.exit(0)
        else:
            print(f"✗ Validation failed: {error}")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Error while validating AWS configuration: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
