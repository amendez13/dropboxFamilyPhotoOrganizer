"""
Local debugging dashboard for AWS Rekognition matches.

Builds a thumbnail grid for the configured Dropbox source folder and
highlights matches in green and non-matches in red.
"""

from __future__ import annotations

import argparse
import base64
import glob
import html
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, List, Optional

import yaml

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.auth.client_factory import DropboxClientFactory  # noqa: E402
from scripts.dropbox_client import DropboxClient  # noqa: E402
from scripts.face_recognizer import get_provider  # noqa: E402
from scripts.face_recognizer.base_provider import BaseFaceRecognitionProvider  # noqa: E402


@dataclass
class ImageEntry:
    path: str
    matched: bool
    num_matches: int
    total_faces: int
    thumbnail_base64: str


@dataclass
class CachePayload:
    cache_key: str
    generated_at: str
    entries: List[ImageEntry]


def load_config(config_path: str) -> Dict[str, Any]:
    if os.path.isabs(config_path):
        full_path = config_path
    else:
        full_path = os.path.abspath(os.path.join(PROJECT_ROOT, config_path))

    with open(full_path, "r") as f:
        return yaml.safe_load(f) or {}


def _get_reference_photos(reference_photos_dir: str, image_extensions: List[str]) -> List[str]:
    photos: List[str] = []
    for ext in image_extensions:
        pattern = os.path.join(reference_photos_dir, f"*{ext}")
        photos.extend([p for p in glob.glob(pattern) if not os.path.basename(p).startswith(".")])
    return list(set(photos))


def list_image_files(
    dbx_client: DropboxClient, source_folder: str, destination_folder: str, image_extensions: List[str]
) -> List[str]:
    files = list(dbx_client.list_folder_recursive(source_folder))
    image_files = []
    for entry in files:
        path_lower = entry.path_lower
        if path_lower.startswith(destination_folder.lower()):
            continue
        if any(path_lower.endswith(ext.lower()) for ext in image_extensions):
            image_files.append(entry.path_display)
    return image_files


def build_cache_key(
    source_folder: str,
    destination_folder: str,
    face_config: Dict[str, Any],
    processing: Dict[str, Any],
    limit: int,
) -> str:
    payload = {
        "source_folder": source_folder,
        "destination_folder": destination_folder,
        "provider": face_config.get("provider", "local"),
        "tolerance": face_config.get("tolerance", 0.6),
        "thumbnail_size": face_config.get("thumbnail_size", "w256h256"),
        "image_extensions": processing.get("image_extensions", [".jpg", ".jpeg", ".png", ".heic"]),
        "limit": limit,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return base64.b64encode(encoded).decode("ascii")


def load_cache(cache_file: str, cache_key: str, logger: logging.Logger) -> Optional[List[ImageEntry]]:
    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "r") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Unable to read cache file, rebuilding: {e}")
        return None

    if payload.get("cache_key") != cache_key:
        logger.info("Cache key mismatch, rebuilding dashboard data")
        return None

    entries = [
        ImageEntry(
            path=item["path"],
            matched=item["matched"],
            num_matches=item["num_matches"],
            total_faces=item["total_faces"],
            thumbnail_base64=item["thumbnail_base64"],
        )
        for item in payload.get("entries", [])
    ]
    logger.info(f"Loaded {len(entries)} cached entries")
    return entries


def save_cache(cache_file: str, cache_key: str, entries: List[ImageEntry], logger: logging.Logger) -> None:
    cache_dir = os.path.dirname(cache_file)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
    payload = {
        "cache_key": cache_key,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": [
            {
                "path": entry.path,
                "matched": entry.matched,
                "num_matches": entry.num_matches,
                "total_faces": entry.total_faces,
                "thumbnail_base64": entry.thumbnail_base64,
            }
            for entry in entries
        ],
    }

    try:
        with open(cache_file, "w") as f:
            json.dump(payload, f)
    except OSError as e:
        logger.warning(f"Unable to write cache file: {e}")


def build_entries(
    dbx_client: DropboxClient,
    provider: BaseFaceRecognitionProvider,
    face_config: Dict[str, Any],
    image_paths: List[str],
    tolerance: float,
    limit: int,
    logger: logging.Logger,
) -> List[ImageEntry]:
    entries: List[ImageEntry] = []
    thumbnail_size = face_config.get("thumbnail_size", "w256h256")

    for idx, path in enumerate(image_paths):
        if limit and idx >= limit:
            break
        logger.info(f"Processing {idx + 1}/{len(image_paths)}: {path}")

        image_data = dbx_client.get_thumbnail(path, size=thumbnail_size)
        if not image_data:
            logger.warning(f"Failed to fetch thumbnail: {path}")
            continue

        matches, total_faces = provider.find_matches_in_image(image_data, source=path, tolerance=tolerance)
        entry = ImageEntry(
            path=path,
            matched=bool(matches),
            num_matches=len(matches),
            total_faces=total_faces,
            thumbnail_base64=base64.b64encode(image_data).decode("ascii"),
        )
        entries.append(entry)

    return entries


def build_html(entries: List[ImageEntry]) -> str:
    match_count = sum(1 for e in entries if e.matched)
    no_match_count = len(entries) - match_count

    cards = []
    for entry in entries:
        label = f"{entry.num_matches}/{entry.total_faces} faces matched"
        status_class = "match" if entry.matched else "no-match"
        cards.append(
            "\n".join(
                [
                    f'<div class="card {status_class}">',
                    f'  <img src="data:image/jpeg;base64,{entry.thumbnail_base64}" alt="{html.escape(entry.path)}" />',
                    f'  <div class="meta">{html.escape(entry.path)}</div>',
                    f'  <div class="meta">{html.escape(label)}</div>',
                    "</div>",
                ]
            )
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Face Match Debug Dashboard</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #101214;
        --panel: #1b1f24;
        --text: #f2f2f2;
        --muted: #a7b0ba;
        --match: #2ecc71;
        --no-match: #e74c3c;
      }}
      body {{
        margin: 0;
        background: radial-gradient(circle at top, #1e2730 0%, #0f1216 55%, #0b0d10 100%);
        color: var(--text);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      header {{
        padding: 24px 32px 8px;
      }}
      h1 {{
        margin: 0 0 6px;
        font-size: 26px;
        font-weight: 600;
      }}
      .summary {{
        color: var(--muted);
        font-size: 14px;
      }}
      .summary span {{
        display: inline-block;
        margin-right: 16px;
      }}
      .grid {{
        display: grid;
        gap: 16px;
        padding: 24px 32px 48px;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      }}
      .card {{
        background: var(--panel);
        border-radius: 14px;
        overflow: hidden;
        border: 3px solid transparent;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
        display: flex;
        flex-direction: column;
      }}
      .card.match {{
        border-color: var(--match);
      }}
      .card.no-match {{
        border-color: var(--no-match);
      }}
      .card img {{
        width: 100%;
        height: 200px;
        object-fit: cover;
        display: block;
      }}
      .meta {{
        padding: 8px 12px;
        font-size: 12px;
        color: var(--muted);
        line-height: 1.4;
        word-break: break-word;
      }}
      @media (max-width: 720px) {{
        header {{
          padding: 20px 18px 8px;
        }}
        .grid {{
          padding: 16px 18px 36px;
        }}
      }}
    </style>
  </head>
  <body>
    <header>
      <h1>Face Match Debug Dashboard</h1>
      <div class="summary">
        <span>Total: {len(entries)}</span>
        <span>Matches: {match_count}</span>
        <span>No Match: {no_match_count}</span>
      </div>
    </header>
    <section class="grid">
      {"".join(cards)}
    </section>
  </body>
</html>
"""


def run_server(html_payload: str, host: str, port: int, logger: logging.Logger) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in ("/", "/index.html"):
                self.send_response(404)
                self.end_headers()
                return

            data = html_payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    server = HTTPServer((host, port), Handler)
    logger.info(f"Dashboard available at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down dashboard server")
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="AWS Rekognition debug dashboard")
    parser.add_argument("--config", default="config/config.yaml", help="Path to configuration file")
    parser.add_argument("--host", default="127.0.0.1", help="Host for the local server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the local server")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of images processed (0 = no limit)")
    parser.add_argument(
        "--cache-file",
        default="logs/debug_dashboard_cache.json",
        help="Path to cache file for persisted results",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Rebuild cache by re-running inference",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger = logging.getLogger("debug_dashboard")

    config = load_config(args.config)
    dropbox_config = config.get("dropbox", {})
    face_config = config.get("face_recognition", {})
    processing = config.get("processing", {})

    source_folder = dropbox_config.get("source_folder")
    destination_folder = dropbox_config.get("destination_folder")
    if not source_folder or not destination_folder:
        logger.error("source_folder and destination_folder must be set in config")
        return 1

    tolerance = face_config.get("tolerance", 0.6)
    image_extensions = processing.get("image_extensions", [".jpg", ".jpeg", ".png", ".heic"])
    reference_photos_dir = face_config.get("reference_photos_dir", "./reference_photos")

    if not os.path.isabs(reference_photos_dir):
        reference_photos_dir = os.path.abspath(os.path.join(PROJECT_ROOT, reference_photos_dir))

    factory = DropboxClientFactory(config)
    dbx_client = factory.create_client()

    provider_name = face_config.get("provider", "local")
    provider_config = dict(face_config)
    provider_config.update(face_config.get(provider_name, {}))
    provider_config["tolerance"] = tolerance
    provider = get_provider(provider_name, provider_config)

    reference_photos = _get_reference_photos(reference_photos_dir, image_extensions)
    if not reference_photos:
        logger.error(f"No reference photos found in {reference_photos_dir}")
        return 1

    provider.load_reference_photos(reference_photos)

    image_paths = list_image_files(dbx_client, source_folder, destination_folder, image_extensions)
    if not image_paths:
        logger.warning("No image files found in source folder")
        return 0

    cache_key = build_cache_key(source_folder, destination_folder, face_config, processing, args.limit)
    entries = None if args.refresh_cache else load_cache(args.cache_file, cache_key, logger)

    if entries is None:
        entries = build_entries(
            dbx_client=dbx_client,
            provider=provider,
            face_config=face_config,
            image_paths=image_paths,
            tolerance=tolerance,
            limit=args.limit,
            logger=logger,
        )
        save_cache(args.cache_file, cache_key, entries, logger)

    html_payload = build_html(entries)
    run_server(html_payload, args.host, args.port, logger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
