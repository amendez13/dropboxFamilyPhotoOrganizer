# AWS Face Recognition Setup Guide

This guide provides step-by-step instructions for setting up the AWS Rekognition provider for face recognition in the Dropbox Photo Organizer.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
  - [Creating an AWS Account](#creating-an-aws-account)
  - [Creating an IAM User](#creating-an-iam-user)
  - [IAM Policy Configuration](#iam-policy-configuration)
  - [Getting Access Keys](#getting-access-keys)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Config File Settings](#config-file-settings)
  - [Credential Options](#credential-options)
- [First Run](#first-run)
- [API Usage and Costs](#api-usage-and-costs)
  - [Pricing Breakdown](#pricing-breakdown)
  - [Free Tier](#free-tier)
  - [Rate Limits](#rate-limits)
  - [Cost Optimization Tips](#cost-optimization-tips)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)
- [Comparison with Other Providers](#comparison-with-other-providers)
- [Next Steps](#next-steps)

---

## Overview

The AWS Rekognition provider offers cloud-based face recognition using Amazon's machine learning services. It provides:

**Advantages:**
- **High Accuracy**: Industry-leading face recognition models
- **Fast Processing**: Optimized for high throughput
- **Scalability**: Handles large photo libraries efficiently
- **No Local Setup**: No need to install dlib or compile C++ libraries
- **Simple Integration**: Direct image comparison without person groups or training
- **Flexible Authentication**: Multiple credential options (config file, AWS CLI, IAM roles)

**Trade-offs:**
- Requires AWS account and credentials
- API costs per image processed ($1 per 1,000 images)
- Photos sent to AWS for processing (privacy consideration)
- Requires internet connection
- Data not persisted between sessions (compares images directly)

---

## Prerequisites

Before starting, ensure you have:

1. **Python 3.8 or higher** installed
2. **An AWS account** (free tier available)
3. **A credit card** for AWS verification (free tier won't charge you)
4. **The Dropbox Photo Organizer** project set up

---

## AWS Account Setup

### Creating an AWS Account

1. **Visit the AWS Console**: Go to [https://aws.amazon.com/console/](https://aws.amazon.com/console/)

2. **Sign up for a free account** if you don't have one:
   - Click "Create an AWS Account"
   - Enter your email address and choose an account name
   - Complete the verification process (phone and credit card)
   - Select the "Basic Support - Free" plan
   - You'll receive 12 months of free tier access

3. **Access the AWS Console**: After signing up, you'll be redirected to the AWS Management Console

### Creating an IAM User

For security best practices, create a dedicated IAM user for the photo organizer instead of using root credentials.

1. **Navigate to IAM**:
   - Search for "IAM" in the AWS Console search bar
   - Click "IAM" to open Identity and Access Management

2. **Create a new user**:
   - Click "Users" in the left sidebar
   - Click "Create user"
   - Enter a username (e.g., "dropbox-photo-organizer")
   - Click "Next"

3. **Set permissions**:
   - Select "Attach policies directly"
   - Search for and select `AmazonRekognitionReadOnlyAccess`
   - Or create a custom policy (see next section for minimum permissions)
   - Click "Next"

4. **Review and create**:
   - Review the user details
   - Click "Create user"

### IAM Policy Configuration

For minimum required permissions, create a custom policy:

1. **Navigate to Policies**:
   - In IAM, click "Policies" in the left sidebar
   - Click "Create policy"

2. **Use JSON editor**:
   - Click the "JSON" tab
   - Paste the following policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DropboxPhotoOrganizerRekognition",
            "Effect": "Allow",
            "Action": [
                "rekognition:DetectFaces",
                "rekognition:CompareFaces"
            ],
            "Resource": "*"
        }
    ]
}
```

3. **Name and create**:
   - Click "Next"
   - Name: "DropboxPhotoOrganizerPolicy"
   - Description: "Minimum permissions for Dropbox Photo Organizer face recognition"
   - Click "Create policy"

4. **Attach to user**:
   - Go back to Users → your user
   - Click "Add permissions" → "Attach policies directly"
   - Search for and select "DropboxPhotoOrganizerPolicy"
   - Click "Add permissions"

### Getting Access Keys

1. **Navigate to your IAM user**:
   - In IAM, click "Users"
   - Click on your user (e.g., "dropbox-photo-organizer")

2. **Create access key**:
   - Click the "Security credentials" tab
   - Scroll to "Access keys"
   - Click "Create access key"

3. **Select use case**:
   - Select "Application running outside AWS"
   - Click "Next"

4. **Add description** (optional):
   - Description: "Dropbox Photo Organizer"
   - Click "Create access key"

5. **Save credentials**:
   - **Access key ID**: Copy this value
   - **Secret access key**: Copy this value (shown only once!)
   - Click "Download .csv file" for backup
   - Click "Done"

> **Important**: Store your secret access key securely. You cannot retrieve it again after closing this page.

---

## Installation

### Install Python Dependencies

The AWS provider requires the boto3 SDK:

```bash
# Activate your virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install AWS dependencies
pip install -r requirements-aws.txt
```

Or install manually:

```bash
pip install boto3 botocore
```

### Verify Installation

```python
python -c "import boto3; print('boto3 installed successfully!')"
```

---

## Configuration

### Config File Settings

Edit your `config/config.yaml` file:

```yaml
face_recognition:
  # Set provider to 'aws'
  provider: "aws"

  # Path to reference photos of the target person
  reference_photos_dir: "./reference_photos"

  # Face matching tolerance (not directly used by AWS, but kept for compatibility)
  tolerance: 0.6

  # AWS-specific settings
  aws:
    # AWS credentials (optional if using AWS CLI configuration or IAM roles)
    aws_access_key_id: "YOUR_AWS_ACCESS_KEY_ID"
    aws_secret_access_key: "YOUR_AWS_SECRET_ACCESS_KEY"

    # AWS region for Rekognition API
    # Choose a region close to you for lower latency
    # Available regions: us-east-1, us-west-2, eu-west-1, ap-northeast-1, etc.
    aws_region: "us-east-1"

    # Similarity threshold percentage (0-100)
    # Higher = more strict (fewer false positives)
    # Lower = more lenient (may include false positives)
    # Recommended: 80-90 for accurate matching
    similarity_threshold: 80.0
```

### Credential Options

AWS Rekognition supports three authentication methods (in order of precedence):

#### Option 1: Config File (Simplest)

Add credentials directly to `config/config.yaml`:

```yaml
aws:
  aws_access_key_id: "AKIAIOSFODNN7EXAMPLE"
  aws_secret_access_key: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
  aws_region: "us-east-1"
```

**Pros**: Simple setup, all configuration in one place
**Cons**: Credentials stored in plain text file

#### Option 2: AWS CLI Configuration (Recommended)

Use the AWS CLI to configure credentials:

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure
```

When prompted:
- **AWS Access Key ID**: Enter your access key
- **AWS Secret Access Key**: Enter your secret key
- **Default region name**: Enter your region (e.g., `us-east-1`)
- **Default output format**: Press Enter for default (json)

This stores credentials in `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

Then in `config/config.yaml`, only specify the region:

```yaml
aws:
  aws_region: "us-east-1"
  similarity_threshold: 80.0
```

**Pros**: Secure, reusable across projects, supports profiles
**Cons**: Requires AWS CLI installation

#### Option 3: IAM Roles (For EC2/Lambda)

If running on AWS infrastructure, use IAM roles:

1. Create an IAM role with `AmazonRekognitionReadOnlyAccess` policy
2. Attach the role to your EC2 instance or Lambda function
3. No credentials needed in config:

```yaml
aws:
  aws_region: "us-east-1"
  similarity_threshold: 80.0
```

**Pros**: Most secure, no credentials to manage
**Cons**: Only works on AWS infrastructure

#### Environment Variables

You can also use environment variables:

```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```

---

## First Run

### Step 1: Prepare Reference Photos

1. **Collect 3-10 high-quality photos** of the target person:
   - Clear, well-lit photos
   - Face clearly visible (frontal view preferred)
   - Different angles and expressions help improve accuracy
   - One face per photo (or ensure target face is prominent)
   - Minimum face size: 40x40 pixels

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

   Supported formats: JPG, JPEG, PNG (max 5MB per image)

### Step 2: Test AWS Connection

Create a test script to verify your AWS configuration:

```python
# scripts/aws_tests/test_aws_connection.py
import yaml
from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

aws_config = config['face_recognition']['aws']

# Initialize provider
try:
    provider = AWSFaceRecognitionProvider(aws_config)
    print("✓ AWS Rekognition client initialized")

    # Validate configuration
    is_valid, error = provider.validate_configuration()
    if is_valid:
        print("✓ AWS credentials are valid")
    else:
        print(f"✗ Validation failed: {error}")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run the test:
```bash
source venv/bin/activate
python scripts/aws_tests/test_aws_connection.py
```

### Step 3: Load Reference Photos

Test loading your reference photos:

```python
# scripts/aws_tests/test_aws_reference.py
import yaml
import glob
from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

aws_config = config['face_recognition']['aws']
ref_dir = config['face_recognition']['reference_photos_dir']

# Get reference photos
photos = glob.glob(f"{ref_dir}/*.jpg") + glob.glob(f"{ref_dir}/*.jpeg") + glob.glob(f"{ref_dir}/*.png")
print(f"Found {len(photos)} reference photo(s)")

# Initialize and load references
provider = AWSFaceRecognitionProvider(aws_config)
try:
    face_count = provider.load_reference_photos(photos)
    print(f"✓ Successfully loaded {face_count} reference photo(s)")
    print("  Ready to process Dropbox photos!")
except Exception as e:
    print(f"✗ Error: {e}")
```

Run the test:
```bash
python scripts/aws_tests/test_aws_reference.py
```

### Step 4: Understanding the AWS Process

Unlike Azure, AWS Rekognition uses direct image comparison:

1. **Load Reference Photos**: Images are read and verified to contain faces
2. **Store Image Bytes**: Reference images stored in memory (not in AWS)
3. **Compare Faces**: Each candidate photo is compared against all reference images
4. **No Training Required**: Comparisons happen in real-time

This approach means:
- No setup delay (no training step)
- Each comparison is an API call
- Reference images must be loaded each session

---

## API Usage and Costs

### Pricing Breakdown

AWS Rekognition pricing is based on the number of images processed:

| Operation | Price (per 1,000 images) |
|-----------|--------------------------|
| DetectFaces | $1.00 |
| CompareFaces | $1.00 |

**Example**: Processing 5,000 photos with 3 reference images:
- Reference photo face detection: 3 × $0.001 = $0.003
- Candidate photo comparisons: 5,000 × 3 × $0.001 = $15.00
- **Total**: ~$15.00

### Free Tier

AWS Free Tier includes (first 12 months):
- **5,000 images/month** for face detection
- **5,000 images/month** for face comparison

After free tier:
- Standard pricing applies
- No monthly minimum

### Rate Limits

Default AWS Rekognition quotas:

| Quota | Default Limit |
|-------|---------------|
| Transactions per second (TPS) | 50 |
| Max faces per image | 100 |
| Max image size | 5 MB (API), 15 MB (S3) |
| Min face size | 40×40 pixels |
| Max image dimensions | 4096×4096 pixels |

**To request limit increases**:
1. Go to AWS Service Quotas
2. Select "Amazon Rekognition"
3. Request increase for needed quotas

### Cost Optimization Tips

1. **Use thumbnails**: Process 256×256 thumbnails instead of full images
2. **Fewer reference photos**: 3-5 good photos often suffice
3. **Filter by date**: Only process photos from specific date ranges
4. **Cache results**: Don't reprocess already-matched photos
5. **Batch processing**: Process photos in batches during off-peak hours
6. **Monitor usage**: Check AWS Cost Explorer regularly
7. **Set billing alerts**: Configure AWS Budgets to alert on spending

**Setting up a billing alert**:
```bash
# Using AWS CLI
aws budgets create-budget \
    --account-id YOUR_ACCOUNT_ID \
    --budget file://budget.json \
    --notifications-with-subscribers file://notifications.json
```

---

## Troubleshooting

### Authentication Errors

**"boto3 library not installed"**
```bash
pip install boto3 botocore
```

**"Failed to initialize AWS Rekognition client: NoCredentialsError"**
- Check if credentials are configured correctly
- Verify `~/.aws/credentials` file exists (if using AWS CLI)
- Ensure config.yaml has correct credentials
- Try running `aws sts get-caller-identity` to test credentials

**"AccessDeniedException: User is not authorized"**
- Verify IAM user has `rekognition:DetectFaces` and `rekognition:CompareFaces` permissions
- Check the IAM policy is attached to the user
- Ensure you're using the correct AWS account

**"InvalidSignatureException"**
- Check for whitespace in access keys
- Verify system clock is synchronized
- Regenerate access keys if issue persists

### Region Errors

**"Could not connect to the endpoint URL"**
- Verify the region supports Rekognition (not all regions do)
- Supported regions: us-east-1, us-east-2, us-west-2, eu-west-1, eu-west-2, ap-northeast-1, ap-southeast-2, etc.
- Update `aws_region` in config

### Rate Limit Errors

**"ProvisionedThroughputExceededException" or "ThrottlingException"**
- You've exceeded the TPS limit
- Wait and retry (automatic with retry logic)
- Request a quota increase via AWS Service Quotas
- Reduce processing speed by adding delays

### Image Errors

**"InvalidImageFormatException"**
- Image format not supported (use JPG, PNG)
- Image may be corrupted
- Try converting the image: `convert input.heic output.jpg`

**"ImageTooLargeException"**
- Image exceeds 5 MB
- Resize image before processing
- Use thumbnails for initial detection

**"InvalidParameterException: No faces detected"**
- Face is too small (< 40×40 pixels)
- Image is too dark or blurry
- Try a clearer reference photo
- Face may be obscured or at extreme angle

### Service Errors

**"InternalServerError"**
- AWS service issue (temporary)
- Retry the request (automatic with retry logic)
- Check AWS Service Health Dashboard

**"ServiceUnavailableException"**
- AWS is experiencing issues
- Wait and retry
- Check AWS status page: https://status.aws.amazon.com/

---

## Security Considerations

### Credential Management

1. **Never commit credentials** to version control
   - Add `config/config.yaml` to `.gitignore`
   - Use `config.example.yaml` for templates

2. **Use IAM best practices**:
   - Create dedicated IAM user for this application
   - Use minimum required permissions (see IAM policy above)
   - Rotate access keys regularly (every 90 days)
   - Enable MFA on your AWS account

3. **Use environment variables** for production:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   ```

4. **Consider AWS Secrets Manager** for enterprise deployments

### Data Privacy

When using AWS Rekognition:

- **Images are sent to AWS** for processing
- **Images are NOT stored** by AWS after processing
- **Results are NOT stored** by AWS
- **Data residency**: Processed in the region you specify
- **Compliance**: AWS is SOC, PCI DSS, HIPAA, GDPR compliant

**For sensitive photos**, consider:
- Using the local provider instead (no cloud processing)
- Reviewing AWS's [Data Privacy FAQ](https://aws.amazon.com/compliance/data-privacy-faq/)
- Implementing data retention policies

### GDPR/CCPA Considerations

If processing photos of EU/California residents:

1. **Obtain consent** before processing biometric data
2. **Document the purpose** of face recognition
3. **Provide deletion options** (delete reference photos)
4. **Review AWS's compliance** documentation

Note: AWS Rekognition does not store face data between API calls, which simplifies compliance. All face comparison happens in real-time.

---

## Comparison with Other Providers

| Feature | AWS Rekognition | Azure Face API | Local (dlib) |
|---------|-----------------|----------------|--------------|
| **Accuracy** | Very High | Very High | High |
| **Setup Complexity** | Medium | Medium | High (dlib compile) |
| **Internet Required** | Yes | Yes | No |
| **Cost** | $1/1,000 images | $1/1,000 images | Free |
| **Free Tier** | 5,000/month (12 mo) | 30,000/month | Unlimited |
| **Data Storage** | None (real-time) | Optional (person groups) | Local only |
| **Training Required** | No | Yes | No |
| **Rate Limit** | 50 TPS | 10-20 TPS | Unlimited |
| **Privacy** | Cloud processing | Cloud processing | Local only |

**Choose AWS Rekognition when:**
- You want simple setup without training steps
- You prefer AWS ecosystem and already have AWS account
- You need high throughput (50 TPS default)
- You want no data persistence (privacy advantage)

**Choose Azure Face API when:**
- You want persistent face data (person groups)
- You prefer Microsoft ecosystem
- You have higher free tier needs (30K/month vs 5K/month)

**Choose Local (dlib) when:**
- Privacy is paramount (no cloud processing)
- You have limited or no internet access
- You want zero API costs
- You don't mind the dlib installation complexity

---

## Next Steps

Once your AWS Rekognition provider is set up:

1. **Configure Dropbox access** (see [DROPBOX_SETUP.md](./DROPBOX_SETUP.md))
2. **Set source and destination folders** in `config/config.yaml`
3. **Run with dry-run mode** first:
   ```bash
   python scripts/organize_photos.py --dry-run
   ```
4. **Optional: Review matches in the debug dashboard**
   ```bash
   python scripts/debug_dashboard.py
   ```
4. **Review matches** and adjust `similarity_threshold` if needed:
   - Increase (e.g., 85-90) for fewer false positives
   - Decrease (e.g., 70-75) for more matches (may include false positives)
5. **Run actual processing** when satisfied with results

---

## References

- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [AWS Rekognition Python SDK (boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html)
- [AWS Rekognition Pricing](https://aws.amazon.com/rekognition/pricing/)
- [AWS Rekognition Quotas](https://docs.aws.amazon.com/rekognition/latest/dg/limits.html)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Security Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- [AWS GDPR Compliance](https://aws.amazon.com/compliance/gdpr-center/)
