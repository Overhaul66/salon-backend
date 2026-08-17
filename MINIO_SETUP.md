# MinIO Setup Guide

This guide explains how to set up and use MinIO for image storage in the Salon Management backend.

## Overview

MinIO is used as an S3-compatible object storage solution for storing images (salon logos, cover images, gallery images, and user profile pictures). When enabled, all `ImageField` uploads will be stored in MinIO instead of the local filesystem.

## Prerequisites

- Docker and Docker Compose installed
- MinIO service added to `docker-compose.yml`

## Configuration

### 1. Environment Variables

The following environment variables control MinIO configuration:

#### In `local.env` (for local development):
```env
USE_MINIO=True
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_USE_HTTPS=False
MINIO_MEDIA_BUCKET_NAME=media
MINIO_STATIC_BUCKET_NAME=static
```

#### In `docker-compose.yml` (for Docker):
```yaml
environment:
  - MINIO_ENDPOINT=minio
  - MINIO_ACCESS_KEY=minioadmin
  - MINIO_SECRET_KEY=minioadmin
  - MINIO_USE_HTTPS=False
  - MINIO_MEDIA_BUCKET_NAME=media
```

### 2. Django Settings

MinIO is configured in `config/settings.py`. When `USE_MINIO=True`, the application uses S3Boto3Storage backend with MinIO. When `USE_MINIO=False`, it falls back to local filesystem storage.

## Getting Started

### 1. Start MinIO Service

```bash
docker-compose up -d minio
```

### 2. Initialize MinIO Buckets

Run the management command to create the required buckets with public read access:

```bash
# If using Docker:
docker-compose exec web python manage.py init_minio

# If running locally:
python manage.py init_minio
```

This creates two buckets with **public read access**:
- `media` - for user-uploaded images (publicly readable)
- `static` - for static files (publicly readable)

**Note**: The buckets are publicly readable so images can be accessed directly via URL. Write operations remain restricted to your Django application.

### 3. Access MinIO Console

MinIO provides a web-based console for managing files:

- **URL**: http://localhost:9001
- **Username**: minioadmin
- **Password**: minioadmin

From the console, you can:
- View uploaded files
- Delete files
- Monitor storage usage
- Configure bucket policies

## How It Works

### Image Upload Flow

1. Client sends a POST/PUT request with an image file to an API endpoint (e.g., updating salon logo)
2. Django's `ImageField` saves the file using the configured storage backend
3. When `USE_MINIO=True`, the file is uploaded to MinIO via the S3 API
4. The image URL is stored in the database as a relative path
5. When serializing, Django constructs the full URL using `MEDIA_URL` (e.g., `http://localhost:9000/media/salon_logos/example.jpg`)

### Models Using MinIO

The following models store images in MinIO when enabled:

- **Salon** (`apps/salons/models.py`):
  - `logo` - Salon logo image
  - `cover_image` - Salon cover image

- **SalonImage** (`apps/salons/models.py`):
  - `image` - Gallery images for salons

- **CustomUser** (`apps/users/models.py`):
  - `profile_picture` - User profile pictures

## API Endpoints

All existing API endpoints that handle image uploads work seamlessly with MinIO. No changes to views or serializers are needed.

### Example: Update Salon Logo

```http
PATCH /api/salons/salons/me/
Content-Type: multipart/form-data

{
  "logo": <image_file>
}
```

### Example Response

```json
{
  "id": "uuid",
  "name": "Salon Name",
  "logo": "http://localhost:9000/media/salon_logos/logo_123456.jpg",
  ...
}
```

## Utility Functions

The `apps/common/utils.py` module provides helper functions for MinIO operations:

```python
from apps.common.utils import (
    get_minio_client,          # Get MinIO client instance
    get_minio_url,             # Generate full MinIO URL
    delete_from_minio,         # Delete an object from MinIO
    get_presigned_url,         # Generate temporary access URL
    list_bucket_objects,       # List objects in a bucket
)
```

### Example Usage

```python
from apps.common.utils import get_minio_url, delete_from_minio

# Get full URL for an image
url = get_minio_url('media', 'salon_logos/logo.jpg')
# Returns: 'http://localhost:9000/media/salon_logos/logo.jpg'

# Delete an image from MinIO
delete_from_minio('media', 'salon_logos/old_logo.jpg')
```

## Switching Between Local and MinIO Storage

### To use MinIO:
Set `USE_MINIO=True` in your environment variables.

### To use local filesystem:
Set `USE_MINIO=False` or remove the variable (defaults to False).

**Note**: When switching from MinIO to local storage (or vice versa), existing images will not be migrated automatically. You'll need to manually copy files or update database records.

## Bucket Access & Security

### Public Read Access

The MinIO buckets are configured with **public read access** by default. This means:

- ✅ Anyone can view/download images via direct URL
- ✅ Frontend can display images without authentication
- ✅ Images are accessible at: `http://localhost:9000/media/{image_path}`
- ❌ Only your Django app can upload/delete files (requires credentials)

This is the recommended setup for public-facing content like salon images, logos, and profile pictures.

### Changing Bucket Policies

If you need to restrict access later:

1. **Via MinIO Console** (http://localhost:9001):
   - Go to Buckets → Select bucket → Access Policy
   - Choose "Custom" and paste a policy JSON

2. **Via Django Management Command**:
   ```python
   # Example: Make bucket private
   client.delete_bucket_policy(bucket_name)
   ```

3. **Example Private Bucket Policy**:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Deny",
         "Principal": {"AWS": "*"},
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::media/*"
       }
     ]
   }
   ```

## Production Considerations

### 1. Security

- **Change default credentials**: Update `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` in production
- **Use HTTPS**: Set `MINIO_USE_HTTPS=True` and configure SSL certificates
- **Restrict bucket access**: Configure bucket policies in MinIO console
- **Use environment variables**: Never hardcode credentials in code

### 2. Backup

MinIO data is stored in a Docker volume (`minio_data`). To backup:

```bash
# Backup volume
docker-compose stop minio
docker run --rm -v salon_minio_data:/data -v $(pwd):/backup alpine tar cvf /backup/minio_backup.tar /data

# Restore volume
docker-compose stop minio
docker run --rm -v salon_minio_data:/data -v $(pwd):/backup alpine tar xvf /backup/minio_backup.tar
docker-compose start minio
```

### 3. Scaling

For production, consider:
- Using a MinIO cluster for high availability
- Setting up CDN (e.g., Cloudflare) in front of MinIO
- Configuring lifecycle policies for old images
- Monitoring disk space and performance

## Troubleshooting

### MinIO connection refused

Ensure MinIO service is running:
```bash
docker-compose ps minio
docker-compose logs minio
```

### Bucket creation fails

Check MinIO credentials and endpoint in environment variables. Ensure the MinIO service is healthy:
```bash
docker-compose exec minio curl http://localhost:9000/minio/health/live
```

### Images not loading

1. Check `MEDIA_URL` in Django settings
2. Verify MinIO bucket exists and contains the file
3. Check CORS configuration if accessing from browser
4. Ensure `USE_MINIO=True` is set in environment

### Permission denied errors

- Verify MinIO credentials are correct
- Check bucket policies in MinIO console
- Ensure the Django app has network access to MinIO port 9000

## Migration from Local Storage

If you have existing images in local storage and want to migrate to MinIO:

1. Keep `USE_MINIO=False` temporarily
2. Upload all existing local images to MinIO using the console or mc (MinIO client)
3. Update database records to point to MinIO URLs
4. Set `USE_MINIO=True`
5. Test thoroughly before deploying

## Additional Resources

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [django-storages Documentation](https://django-storages.readthedocs.io/)
- [S3Boto3Storage](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html)