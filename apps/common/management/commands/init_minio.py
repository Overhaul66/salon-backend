import json
from django.core.management.base import BaseCommand
from django.conf import settings
import boto3
from botocore.exceptions import ClientError


class Command(BaseCommand):
    help = "Initialize MinIO buckets for media and static files with public read access"

    def get_s3_client(self):
        """
        Get a boto3 S3 client configured for MinIO
        """
        return boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

    def set_public_read_policy(self, client, bucket_name):
        """
        Set a bucket policy that allows public read access
        """
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }

        try:
            client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(policy)
            )
            self.stdout.write(
                self.style.SUCCESS(f"Public read policy set for bucket: {bucket_name}")
            )
            return True
        except ClientError as e:
            self.stdout.write(
                self.style.WARNING(f"Could not set public policy for {bucket_name}: {e}")
            )
            return False

    def handle(self, *args, **options):
        if not getattr(settings, "USE_MINIO", False):
            self.stdout.write(
                self.style.WARNING("MinIO is not enabled. Set USE_MINIO=True in environment variables.")
            )
            return

        # Get MinIO configuration from settings
        endpoint_url = settings.AWS_S3_ENDPOINT_URL
        media_bucket = settings.AWS_STORAGE_BUCKET_NAME

        # Initialize boto3 S3 client
        client = self.get_s3_client()

        # Create bucket if it doesn't exist and set public read policy
        try:
            # Check if bucket exists
            try:
                client.head_bucket(Bucket=media_bucket)
                self.stdout.write(
                    self.style.SUCCESS(f"Bucket already exists: {media_bucket}")
                )
            except ClientError:
                # Bucket doesn't exist, create it
                client.create_bucket(Bucket=media_bucket)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully created bucket: {media_bucket}")
                )

            # Set public read policy
            self.set_public_read_policy(client, media_bucket)

        except ClientError as e:
            self.stdout.write(
                self.style.ERROR(f"Error with bucket {media_bucket}: {e}")
            )

        self.stdout.write(self.style.SUCCESS("MinIO initialization completed!"))
        self.stdout.write(
            self.style.SUCCESS(
                f"\nYou can now access public files via:\n"
                f"  Media: {endpoint_url}/{media_bucket}/\n"
                f"  Console: http://localhost:9001"
            )
        )