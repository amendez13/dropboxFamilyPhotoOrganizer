# Face Recognition Tuning Notebook Guide

This guide explains how to use the Jupyter notebook for training, evaluating, and tuning face recognition models.

## Prerequisites

1. **Install dependencies**:
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install face_recognition library** (if not already installed):
   - See [FACE_RECOGNITION_LOCAL_SETUP.md](FACE_RECOGNITION_LOCAL_SETUP.md) for detailed instructions

3. **Add reference photos**:
   - Place 3-10 clear photos of the target person in `reference_photos/`
   - Supported formats: .jpg, .jpeg, .png, .heic

## Starting the Notebook

```bash
source venv/bin/activate
cd notebooks
jupyter notebook face_recognition_tuning.ipynb
```

Or use JupyterLab:
```bash
jupyter lab notebooks/face_recognition_tuning.ipynb
```

## Notebook Sections

### Section 1: Setup & Configuration

Loads required libraries and configuration from `config/config.yaml`. Run this first every time you open the notebook.

### Section 2: Reference Photos & Training

- Displays your reference photos in a grid
- Trains the model with current parameters
- Shows training statistics (photos processed, faces detected, success rate)

**Output example**:
```
Training Results:
  Photos processed: 10
  Faces detected: 9
  Success rate: 90.0%
  Training time: 12.34s
```

### Section 3: Test Dataset Creation

Before evaluating the model, you need a labeled test dataset.

**Create the folder structure**:
```
notebooks/data/test_photos/
├── match/       # Photos containing the target person
└── no_match/    # Photos NOT containing the target person
```

**Tips for creating a good test dataset**:
- Include 20-50 photos in each folder for reliable metrics
- Use photos from different sources than your reference photos
- Include challenging cases (different lighting, angles, partial faces)
- For `no_match/`, include photos of other people, not just empty scenes

### Section 4: Run Evaluation

Processes all test photos and records:
- Prediction (match/no_match)
- Confidence score
- Processing time
- Any errors encountered

### Section 5: Metrics & Visualization

Displays performance metrics and visualizations:

| Metric | Description |
|--------|-------------|
| **Accuracy** | Overall correct predictions / total |
| **Precision** | True matches / all predicted matches |
| **Recall** | True matches / all actual matches |
| **F1 Score** | Harmonic mean of precision and recall |
| **AUC** | Area under ROC curve |

**Visualizations**:
- Confusion matrix
- ROC curve
- Confidence score distributions
- Precision-Recall curve

### Section 6: Parameter Grid Search

Test different parameter combinations to find optimal settings.

**Default small grid** (faster):
```python
PARAM_GRID_SMALL = {
    'tolerance': [0.5, 0.6],
    'model': ['hog'],
    'encoding_model': ['large'],
    'num_jitters': [10]
}
```

**Full grid** (exhaustive, slower):
```python
PARAM_GRID_FULL = {
    'tolerance': [0.4, 0.5, 0.6, 0.7],
    'model': ['hog', 'cnn'],
    'encoding_model': ['small', 'large'],
    'num_jitters': [1, 10, 50]
}
```

Change `param_grid = PARAM_GRID_SMALL` to `param_grid = PARAM_GRID_FULL` for exhaustive search.

### Section 7: Experiment Tracking

Save and compare experiments over time.

**Saved experiment format** (JSON):
```json
{
  "id": "exp_20260104_143052",
  "timestamp": "2026-01-04T14:30:52",
  "parameters": {
    "tolerance": 0.6,
    "model": "hog",
    "encoding_model": "large",
    "num_jitters": 50
  },
  "dataset": {
    "name": "test_photos",
    "match_count": 25,
    "no_match_count": 25
  },
  "results": {
    "accuracy": 0.95,
    "precision": 0.94,
    "recall": 0.96,
    "f1_score": 0.95
  }
}
```

Experiments are saved to `notebooks/experiments/experiments.json`.

## Parameter Tuning Guide

### Tolerance

Controls how strict face matching is (Euclidean distance threshold).

| Value | Effect |
|-------|--------|
| 0.4 | Very strict - fewer false positives, more false negatives |
| 0.5 | Strict - good balance for high-precision needs |
| 0.6 | Default - balanced precision and recall |
| 0.7 | Permissive - fewer false negatives, more false positives |

**When to adjust**:
- Lower tolerance if you're getting too many false matches
- Raise tolerance if the target person isn't being detected

### Model

Face detection algorithm.

| Value | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `hog` | Fast | Good | CPU-only systems, large batches |
| `cnn` | Slow | Better | GPU available, difficult photos |

### Encoding Model

Number of facial landmarks used for encoding.

| Value | Landmarks | Accuracy |
|-------|-----------|----------|
| `small` | 5 | Faster, less accurate |
| `large` | 68 | Slower, more accurate (recommended) |

### Num Jitters

Number of times to re-sample face detection.

| Context | Recommended Value |
|---------|-------------------|
| Training | 50-100 (accuracy matters, one-time cost) |
| Recognition | 1-10 (speed matters, repeated many times) |

## Workflow Example

1. **Initial setup**:
   - Add reference photos to `reference_photos/`
   - Create test dataset in `notebooks/data/test_photos/match/` and `no_match/`

2. **Baseline evaluation**:
   - Run Sections 1-5 with default parameters
   - Note baseline metrics (accuracy, F1 score)

3. **Parameter tuning**:
   - Run Section 6 with `PARAM_GRID_SMALL`
   - Identify promising parameter combinations
   - Run again with focused grid around best parameters

4. **Save best configuration**:
   - Update `config/config.yaml` with optimal parameters
   - Save experiment for future reference

5. **Iterate**:
   - Add more test photos for edge cases
   - Re-evaluate with expanded dataset

## Troubleshooting

### "No test photos found"

Create the test dataset folders and add photos:
```bash
mkdir -p notebooks/data/test_photos/match
mkdir -p notebooks/data/test_photos/no_match
# Add photos to each folder
```

### "No faces detected in reference photos"

- Ensure faces are clearly visible and well-lit
- Try using `model: 'cnn'` for better detection
- Check that photos are valid image files

### Slow processing

- Use `model: 'hog'` instead of `'cnn'`
- Reduce `num_jitters` for recognition (keep high for training)
- Use smaller test dataset for initial tuning

### Low accuracy

- Add more diverse reference photos (different angles, lighting)
- Adjust tolerance (lower for precision, higher for recall)
- Check test dataset labels are correct
- Try `encoding_model: 'large'` if using `'small'`

## File Locations

| Path | Purpose |
|------|---------|
| `notebooks/face_recognition_tuning.ipynb` | Main notebook |
| `notebooks/data/test_photos/match/` | Test photos with target person |
| `notebooks/data/test_photos/no_match/` | Test photos without target person |
| `notebooks/experiments/experiments.json` | Saved experiment history |
| `reference_photos/` | Reference photos of target person |
| `config/config.yaml` | Configuration file |
