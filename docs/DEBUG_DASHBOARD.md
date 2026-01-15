# Debug Dashboard

Local web dashboard for reviewing AWS face match results using Dropbox thumbnails.

## What It Does

- Loads images from the configured Dropbox `source_folder`
- Fetches thumbnails from Dropbox
- Runs face matching using the configured provider (AWS in your config)
- Shows a grid with:
  - Green borders for matched faces
  - Red borders for non-matches

## Run It

```bash
source venv/bin/activate
python scripts/debug_dashboard.py
```

Open `http://127.0.0.1:8000` in your browser.

### Options

```bash
python scripts/debug_dashboard.py --host 127.0.0.1 --port 8000 --limit 50
```

- `--host`: Host to bind the local server
- `--port`: Port for the dashboard
- `--limit`: Limit number of images processed (0 = all)

## Notes

- Each run makes AWS Rekognition calls and may incur API costs.
- The dashboard uses the thumbnail size defined in `config/config.yaml`.
