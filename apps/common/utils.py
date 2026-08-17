"""
Utility functions for MinIO operations using boto3
"""
from django.conf import settings
import boto3
from botocore.exceptions import ClientError
from urllib.parse import urljoin


def get_minio_client():
    """
    Get a boto3 S3 client configured for MinIO
    """
    if not getattr(settings, "USE_MINIO", False):
        return None

    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def get_minio_url(bucket_name, object_name):
    """
    Generate full MinIO URL for an object
    """
    if not getattr(settings, "USE_MINIO", False):
        return None

    base_url = settings.AWS_S3_ENDPOINT_URL
    return urljoin(base_url, f"{bucket_name}/{object_name}")


def delete_from_minio(bucket_name, object_name):
    """
    Delete an object from MinIO
    """
    client = get_minio_client()
    if not client:
        return False

    try:
        client.delete_object(Bucket=bucket_name, Key=object_name)
        return True
    except ClientError as e:
        print(f"Error deleting object {object_name} from bucket {bucket_name}: {e}")
        return False


def get_presigned_url(bucket_name, object_name, expires=3600):
    """
    Generate a presigned URL for temporary access to an object
    """
    client = get_minio_client()
    if not client:
        return None

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_name},
            ExpiresIn=expires,
        )
        return url
    except ClientError as e:
        print(f"Error generating presigned URL for {object_name}: {e}")
        return None


def list_bucket_objects(bucket_name, prefix=""):
    """
    List all objects in a bucket with optional prefix filter
    """
    client = get_minio_client()
    if not client:
        return []

    try:
        response = client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        return [obj["Key"] for obj in response.get("Contents", [])]
    except ClientError as e:
        print(f"Error listing objects in bucket {bucket_name}: {e}")
        return []