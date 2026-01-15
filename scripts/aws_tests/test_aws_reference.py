"""Verify AWS Rekognition reference photo loading.

Run from project root:
    source venv/bin/activate
    python scripts/aws_tests/test_aws_reference.py
"""

import glob
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
    print(f"ERROR: Could not import AWS provider: {e}")
    sys.exit(2)


def _resolve_ref_dir(ref_dir: str) -> str:
    if not ref_dir:
        return os.path.join(PROJECT_ROOT, "reference_photos")
    if os.path.isabs(ref_dir):
        return ref_dir
    return os.path.join(PROJECT_ROOT, ref_dir)


def main() -> None:
    config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found at {config_path}")
        sys.exit(2)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    face_cfg = config.get("face_recognition", {})
    aws_config = face_cfg.get("aws", {})
    ref_dir = _resolve_ref_dir(face_cfg.get("reference_photos_dir", "./reference_photos"))

    photos = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        photos.extend(glob.glob(os.path.join(ref_dir, ext)))

    print(f"Found {len(photos)} reference photo(s) in {ref_dir}")
    if not photos:
        print("ERROR: No reference photos found")
        sys.exit(1)

    provider = AWSFaceRecognitionProvider(aws_config)
    try:
        face_count = provider.load_reference_photos(photos)
        print(f"OK: Successfully loaded {face_count} reference photo(s)")
        print("  Ready to process Dropbox photos!")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
