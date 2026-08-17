#!/usr/bin/env python
"""
Simple test script to verify MinIO integration
Run this after starting MinIO and initializing buckets:
    python test_minio.py
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from apps.common.utils import get_minio_client, get_minio_url, list_bucket_objects
from PIL import Image
import io

def test_minio_configuration():
    """Test if MinIO is properly configured"""
    print("=" * 60)
    print("Testing MinIO Configuration")
    print("=" * 60)
    
    if not getattr(settings, "USE_MINIO", False):
        print("❌ MinIO is not enabled. Set USE_MINIO=True in environment variables.")
        return False
    
    print("✅ MinIO is enabled")
    print(f"   Endpoint: {settings.AWS_S3_ENDPOINT_URL}")
    print(f"   Media Bucket: {settings.AWS_STORAGE_BUCKET_NAME}")
    return True

def test_minio_connection():
    """Test connection to MinIO"""
    print("\n" + "=" * 60)
    print("Testing MinIO Connection")
    print("=" * 60)
    
    client = get_minio_client()
    if not client:
        print("❌ Failed to create MinIO client")
        return False
    
    print("✅ MinIO client created successfully")
    
    # Test listing buckets
    try:
        response = client.list_buckets()
        bucket_names = [bucket["Name"] for bucket in response.get("Buckets", [])]
        print(f"✅ Connected to MinIO. Found {len(bucket_names)} bucket(s): {bucket_names}")
        
        # Check if required bucket exists
        media_bucket = settings.AWS_STORAGE_BUCKET_NAME
        
        if media_bucket in bucket_names:
            print(f"✅ Media bucket '{media_bucket}' exists")
        else:
            print(f"❌ Media bucket '{media_bucket}' not found. Run: python manage.py init_minio")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error connecting to MinIO: {e}")
        return False

def test_minio_operations():
    """Test basic MinIO operations"""
    print("\n" + "=" * 60)
    print("Testing MinIO Operations")
    print("=" * 60)
    
    client = get_minio_client()
    if not client:
        return False
    
    bucket_name = settings.AWS_STORAGE_BUCKET_NAME
    test_object = "test/test_image.jpg"
    
    # Create a simple test image
    print("Creating test image...")
    image = Image.new('RGB', (100, 100), color='red')
    image_bytes = io.BytesIO()
    image.save(image_bytes, 'JPEG')
    image_bytes.seek(0)
    
    # Test upload
    try:
        print(f"Uploading test image to {bucket_name}/{test_object}...")
        client.put_object(
            Bucket=bucket_name,
            Key=test_object,
            Body=image_bytes,
            ContentType="image/jpeg"
        )
        print("✅ Upload successful")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return False
    
    # Test URL generation
    try:
        url = get_minio_url(bucket_name, test_object)
        print(f"✅ Generated URL: {url}")
    except Exception as e:
        print(f"❌ URL generation failed: {e}")
        return False
    
    # Test listing objects
    try:
        objects = list_bucket_objects(bucket_name, prefix="test/")
        if test_object in objects:
            print(f"✅ Successfully listed objects, found test image")
        else:
            print(f"⚠️  Test image not found in bucket listing")
    except Exception as e:
        print(f"❌ Listing objects failed: {e}")
    
    # Test delete
    try:
        print(f"Deleting test image...")
        from apps.common.utils import delete_from_minio
        if delete_from_minio(bucket_name, test_object):
            print("✅ Delete successful")
        else:
            print("⚠️  Delete failed (non-critical)")
    except Exception as e:
        print(f"⚠️  Delete failed: {e}")
    
    return True

def test_django_storage():
    """Test Django storage backend"""
    print("\n" + "=" * 60)
    print("Testing Django Storage Backend")
    print("=" * 60)
    
    try:
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        print(f"Storage backend: {default_storage.__class__.__name__}")
        
        # Create a test file
        test_content = b"Test content for MinIO integration"
        test_path = "test/test_file.txt"
        
        print(f"Uploading test file via Django storage...")
        default_storage.save(test_path, ContentFile(test_content))
        print("✅ Django storage upload successful")
        
        # Check if file exists
        if default_storage.exists(test_path):
            print(f"✅ File exists in storage: {test_path}")
        else:
            print(f"❌ File not found in storage")
            return False
        
        # Get file URL
        file_url = default_storage.url(test_path)
        print(f"✅ File URL: {file_url}")
        
        # Delete test file
        default_storage.delete(test_path)
        print("✅ Test file deleted")
        
        return True
    except Exception as e:
        print(f"❌ Django storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_image_upload():
    """Test image upload through Django models"""
    print("\n" + "=" * 60)
    print("Testing Image Upload via Django Models")
    print("=" * 60)
    
    try:
        from apps.salons.models import Salon
        from apps.users.models import CustomUser, SalonManager
        from PIL import Image
        import io
        
        # Create a test image
        print("Creating test image...")
        image = Image.new('RGB', (100, 100), color='blue')
        image_bytes = io.BytesIO()
        image.save(image_bytes, 'JPEG')
        image_bytes.seek(0)
        
        from django.core.files.base import ContentFile
        test_image = ContentFile(image_bytes.read(), name='test_salon_logo.jpg')
        
        # Create a test manager user and SalonManager profile
        print("Creating test manager...")
        user = CustomUser.objects.create_user(
            email="test_manager@example.com",
            password="testpass123",
            role="SALON_MANAGER",
        )
        manager = SalonManager.objects.create(user=user)
        
        # Create a test salon (this will upload the image to MinIO)
        print("Creating test salon with logo...")
        salon = Salon(
            name="Test Salon",
            slug="test-salon",
            phone="+1234567890",
            email="test@example.com",
            address="123 Test St",
            city="Test City",
            country="Test Country",
            opening_time="09:00:00",
            closing_time="18:00:00",
            manager=manager,
            logo=test_image
        )
        salon.save()
        
        print(f"✅ Salon created with ID: {salon.id}")
        
        if salon.logo:
            print(f"✅ Logo uploaded successfully: {salon.logo.url}")
        else:
            print("❌ Logo was not uploaded")
            salon.delete()
            return False
        
        # Clean up
        salon.delete()
        manager.delete()
        user.delete()
        print("✅ Test salon deleted")
        
        return True
    except Exception as e:
        print(f"❌ Image upload test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n🧪 MinIO Integration Test Suite\n")
    
    results = []
    
    # Run tests
    results.append(("Configuration", test_minio_configuration()))
    results.append(("Connection", test_minio_connection()))
    
    if results[-1][1]:  # Only test operations if connection succeeded
        results.append(("Operations", test_minio_operations()))
        results.append(("Django Storage", test_django_storage()))
        results.append(("Image Upload", test_image_upload()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s} {status}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! MinIO integration is working correctly.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    from django.core.files.base import ContentFile
    sys.exit(main())