# Azure Face Recognition Setup Guide

This guide provides step-by-step instructions for setting up the Azure Face API provider for face recognition in the Dropbox Photo Organizer.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Azure Account Setup](#azure-account-setup)
  - [Creating an Azure Account](#creating-an-azure-account)
  - [Creating a Face API Resource](#creating-a-face-api-resource)
  - [Getting API Key and Endpoint](#getting-api-key-and-endpoint)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Config File Settings](#config-file-settings)
  - [Understanding Person Groups](#understanding-person-groups)
- [First Training Run](#first-training-run)
- [API Usage and Costs](#api-usage-and-costs)
  - [Pricing Tiers](#pricing-tiers)
  - [Rate Limits](#rate-limits)
  - [Cost Optimization Tips](#cost-optimization-tips)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Next Steps](#next-steps)

---

## Overview

The Azure Face API provider offers cloud-based face recognition using Microsoft's Azure Cognitive Services. It provides:

**Advantages:**
- **High Accuracy**: Enterprise-grade face recognition models
- **Scalability**: Handles large photo libraries efficiently
- **No Local Setup**: No need to install dlib or compile C++ libraries
- **Persistent Storage**: Face data stored in Azure (optional)
- **Advanced Features**: Face identification across person groups

**Trade-offs:**
- Requires Azure account and subscription
- API costs per transaction (30,000 free transactions/month on free tier)
- Photos sent to Azure for processing (privacy consideration)
- Requires internet connection
- More complex initial setup (person groups, training)

---

## Prerequisites

Before starting, ensure you have:

1. **Python 3.8 or higher** installed
2. **An Azure account** (free tier available)
3. **A credit card** for Azure verification (free tier won't charge you)
4. **The Dropbox Photo Organizer** project set up

---

## Azure Account Setup

### Creating an Azure Account

1. **Visit the Azure Portal**: Go to [https://portal.azure.com](https://portal.azure.com)

2. **Sign up for a free account** if you don't have one:
   - Click "Start free"
   - Sign in with a Microsoft account or create a new one
   - Complete the verification process (phone and credit card)
   - You'll receive $200 in credits for the first 30 days

3. **Access the Azure Portal**: After signing up, you'll be redirected to the Azure Portal dashboard

### Creating a Face API Resource

1. **Navigate to "Create a resource"**:
   - Click "+ Create a resource" in the top-left corner
   - Or use the search bar

2. **Search for "Face"**:
   - Type "Face" in the search bar
   - Select "Face" from Azure Cognitive Services

3. **Click "Create"** to configure the resource:

4. **Configure the resource**:
   - **Subscription**: Select your subscription
   - **Resource group**: Create new or use existing (e.g., "dropbox-photo-organizer-rg")
   - **Region**: Choose a region close to you (e.g., "East US", "West Europe")
   - **Name**: Enter a unique name (e.g., "dropbox-face-api")
   - **Pricing tier**: Select "Free F0" for testing (20 calls/minute, 30K calls/month)
     - Or "Standard S0" for production ($1 per 1,000 transactions)

5. **Review and Create**:
   - Click "Review + create"
   - Review settings and click "Create"
   - Wait for deployment (usually 1-2 minutes)

6. **Go to resource**: Click "Go to resource" when deployment completes

### Getting API Key and Endpoint

1. **Navigate to "Keys and Endpoint"**:
   - In your Face resource, click "Keys and Endpoint" in the left menu
   - Under "Resource Management" section

2. **Copy your credentials**:
   - **KEY 1** or **KEY 2**: Either key works (copy one)
   - **Endpoint**: The URL like `https://eastus.api.cognitive.microsoft.com/`

3. **Store securely**:
   - Never commit these to version control
   - Add to your `config/config.yaml` file (gitignored)

---

## Installation

### Install Python Dependencies

The Azure provider requires the Azure Face SDK:

```bash
# Activate your virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install Azure dependencies
pip install -r requirements-azure.txt
```

Or install manually:

```bash
pip install azure-cognitiveservices-vision-face msrest
```

### Verify Installation

```python
python -c "from azure.cognitiveservices.vision.face import FaceClient; print('Azure Face SDK installed successfully!')"
```

---

## Configuration

### Config File Settings

Edit your `config/config.yaml` file:

```yaml
face_recognition:
  # Set provider to 'azure'
  provider: "azure"

  # Path to reference photos of the target person
  reference_photos_dir: "./reference_photos"

  # Face matching tolerance (not directly used by Azure, but kept for compatibility)
  tolerance: 0.6

  # Azure-specific settings
  azure:
    # Your Azure Face API subscription key
    azure_api_key: "YOUR_AZURE_API_KEY_HERE"

    # Your Azure Face API endpoint URL
    azure_endpoint: "https://YOUR_REGION.api.cognitive.microsoft.com"

    # Person Group ID (will be created automatically if not exists)
    # Use a unique identifier for your project
    person_group_id: "dropbox-photo-organizer"

    # Confidence threshold for face matching (0.0 to 1.0)
    # Lower = more strict (fewer false positives)
    # Higher = more lenient (may include false positives)
    confidence_threshold: 0.5

    # Training timeout in seconds (default: 300 = 5 minutes)
    # Increase for large reference photo sets
    training_timeout: 300
```

### Understanding Person Groups

Azure Face API uses a hierarchical structure:

```
Person Group (dropbox-photo-organizer)
└── Person (Target Person)
    ├── Face 1 (from reference_photo_1.jpg)
    ├── Face 2 (from reference_photo_2.jpg)
    └── Face 3 (from reference_photo_3.jpg)
```

**Person Group**: A container for persons. One per project is usually sufficient.

**Person**: Represents the individual you want to find. Created automatically.

**Persisted Faces**: Face data from your reference photos, stored in Azure.

**Training**: After adding faces, the person group must be trained. This happens automatically when you run the photo organizer.

---

## First Training Run

### Step 1: Prepare Reference Photos

1. **Collect 3-10 high-quality photos** of the target person:
   - Clear, well-lit photos
   - Face clearly visible (frontal view preferred)
   - Different angles and expressions help improve accuracy
   - One face per photo (or ensure target face is prominent)

2. **Create the reference photos directory**:
   ```bash
   mkdir -p reference_photos
   ```

3. **Copy photos to the directory**:
   ```bash
   cp /path/to/photo1.jpg reference_photos/
   cp /path/to/photo2.jpg reference_photos/
   cp /path/to/photo3.jpg reference_photos/
   ```

   Supported formats: JPG, JPEG, PNG

### Step 2: Test Azure Connection

Create a test script to verify your Azure configuration:

```python
# test_azure_connection.py
import yaml
from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

azure_config = config['face_recognition']['azure']

# Initialize provider
try:
    provider = AzureFaceRecognitionProvider(azure_config)
    print("✓ Azure Face API client initialized")

    # Validate configuration
    is_valid, error = provider.validate_configuration()
    if is_valid:
        print("✓ Azure API credentials are valid")
    else:
        print(f"✗ Validation failed: {error}")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run the test:
```bash
source venv/bin/activate
python test_azure_connection.py
```

### Step 3: Load Reference Photos

Test loading your reference photos:

```python
# test_azure_training.py
import yaml
import glob
from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

azure_config = config['face_recognition']['azure']
ref_dir = config['face_recognition']['reference_photos_dir']

# Get reference photos
photos = glob.glob(f"{ref_dir}/*.jpg") + glob.glob(f"{ref_dir}/*.jpeg") + glob.glob(f"{ref_dir}/*.png")
print(f"Found {len(photos)} reference photo(s)")

# Initialize and train
provider = AzureFaceRecognitionProvider(azure_config)
try:
    face_count = provider.load_reference_photos(photos)
    print(f"✓ Successfully loaded and trained with {face_count} face(s)")
    print("  Training completed! Ready to process Dropbox photos.")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run the training test:
```bash
python test_azure_training.py
```

### Step 4: Understanding the Training Process

When you load reference photos, the Azure provider:

1. **Creates a Person Group** (if not exists) in Azure
2. **Creates a Person** within the group
3. **Adds faces** from each reference photo to the person
4. **Trains the model** (async operation, may take 10-60 seconds)
5. **Waits for training** to complete before returning

The training is a one-time operation. Subsequent runs will reuse the existing person group and retrain with the provided photos.

---

## API Usage and Costs

### Pricing Tiers

**Free Tier (F0)**:
- 20 transactions per minute
- 30,000 transactions per month
- No cost
- Good for testing and small photo libraries

**Standard Tier (S0)**:
- 10 transactions per second
- No monthly limit
- $1.00 per 1,000 transactions
- Best for production use

### Rate Limits

| Tier | Rate Limit | Monthly Limit |
|------|------------|---------------|
| Free (F0) | 20 calls/minute | 30,000 calls/month |
| Standard (S0) | 10 calls/second | Unlimited |

### Transaction Costs

Each API call counts as a transaction:

| Operation | Transactions |
|-----------|--------------|
| Detect faces | 1 per image |
| Add face to person | 1 per image |
| Identify face | 1 per face |
| Train person group | 1 per training |

**Example**: Processing 1,000 photos with 1 face each:
- Detection: 1,000 transactions
- Identification: 1,000 transactions
- **Total**: ~2,000 transactions = $2.00 (Standard tier)

### Cost Optimization Tips

1. **Use thumbnails first**: Process 256x256 thumbnails instead of full images
2. **Batch processing**: Group API calls when possible
3. **Cache results**: Don't reprocess already-matched photos
4. **Start with free tier**: Test with free tier before upgrading
5. **Monitor usage**: Check Azure Portal for transaction counts

---

## Troubleshooting

### Authentication Errors

**"azure_api_key and azure_endpoint are required"**
- Ensure both `azure_api_key` and `azure_endpoint` are set in config.yaml
- Check for typos in the YAML formatting

**"Azure Face API error: AuthenticationFailed"**
- Verify your API key is correct (copy from Azure Portal)
- Ensure the endpoint URL is correct (includes region)
- Check if your Azure subscription is active

**"Access denied due to invalid subscription key"**
- Your API key may have been regenerated
- Copy the new key from Azure Portal → Keys and Endpoint

### Training Errors

**"Training timed out"**
- Increase `training_timeout` in config (e.g., 600 for 10 minutes)
- Check Azure Portal for training status
- Large reference photo sets take longer to train

**"Training failed: LargeFaceListNotFound"**
- The person group may have been deleted
- Delete `person_group_id` value and let it recreate
- Or manually create via Azure Portal

**"No reference faces could be added"**
- Ensure reference photos contain detectable faces
- Try higher quality photos with clear frontal faces
- Check that photos are valid JPG/PNG files

### Rate Limit Errors

**"Rate limit is exceeded"**
- Wait a minute and try again
- Consider upgrading to Standard tier
- Reduce batch size in processing

**"Out of call volume quota"**
- You've exceeded 30K transactions for the month (Free tier)
- Wait until next month or upgrade to Standard tier

### Face Detection Issues

**"No faces detected in image"**
- Photo may be too dark or blurry
- Face may be too small (< 36x36 pixels)
- Try a clearer reference photo

**"Multiple faces detected"**
- Use photos with only the target person
- Or ensure target face is the largest/most prominent

---

## Security Considerations

### API Key Management

1. **Never commit API keys** to version control
2. **Use environment variables** for production:
   ```bash
   export AZURE_FACE_API_KEY="your-key-here"
   ```
3. **Rotate keys periodically** via Azure Portal
4. **Use separate keys** for development and production

### Data Privacy

When using Azure Face API:

- **Images are sent to Azure** for processing
- **Face data is stored** in Azure if using Person Groups
- **Data residency**: Data stored in the region you selected
- **Compliance**: Azure is GDPR, HIPAA, SOC 2 compliant
- **Retention**: You control data deletion via Person Group management

**For sensitive photos**, consider:
- Using the local provider instead (no cloud processing)
- Deleting person groups after processing
- Reviewing Azure's data handling policies

### GDPR/CCPA Considerations

If processing photos of EU/California residents:

1. **Obtain consent** before processing biometric data
2. **Document the purpose** of face recognition
3. **Provide deletion options** for face data
4. **Implement data retention policies**

To delete all face data from Azure:
```python
# Delete person group (removes all associated data)
provider.client.person_group.delete(person_group_id)
```

---

## Next Steps

Once your Azure Face API provider is set up:

1. **Configure Dropbox access** (see [DROPBOX_SETUP.md](./DROPBOX_SETUP.md))
2. **Set source and destination folders** in `config/config.yaml`
3. **Run with dry-run mode** first:
   ```bash
   python scripts/organize_photos.py --dry-run
   ```
4. **Review matches** and adjust `confidence_threshold` if needed
5. **Run actual processing** when satisfied with results

---

## References

- [Azure Face API Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/face/)
- [Azure Face Python SDK Reference](https://docs.microsoft.com/en-us/python/api/azure-cognitiveservices-vision-face/)
- [Azure Cognitive Services Pricing](https://azure.microsoft.com/en-us/pricing/details/cognitive-services/face-api/)
- [Face API Quotas and Limits](https://docs.microsoft.com/en-us/azure/cognitive-services/face/concepts/face-recognition#input-requirements)
- [GDPR and Azure Cognitive Services](https://docs.microsoft.com/en-us/azure/cognitive-services/cognitive-services-data-privacy)
