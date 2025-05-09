import base64
import os

import firebase_admin
import pytest
from auth import handle_avatar_url, upload_avatar_to_storage
from firebase_admin import credentials, storage

# Sample test data - using a real small JPEG
SAMPLE_IMAGE = b"/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAIAAoDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAb/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="  # 1x1 pixel JPEG
SAMPLE_BASE64 = base64.b64encode(SAMPLE_IMAGE).decode()
SAMPLE_DATA_URI = f"data:image/jpeg;base64,{SAMPLE_BASE64}"


@pytest.fixture(scope="module")
def firebase_app():
    """Initialize Firebase for testing."""
    cred_path = "./firebase-service-account-key.json"
    if not os.path.exists(cred_path):
        pytest.skip("Firebase credentials not found")

    try:
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(
            cred,
            {"storageBucket": "speckle-model-checker.firebasestorage.app"},
            name="test-app",
        )
        yield app
    finally:
        # Clean up the test app
        firebase_admin.delete_app(app)


@pytest.fixture
def storage_bucket(firebase_app):
    """Get a real Firebase Storage bucket."""
    return storage.bucket()


@pytest.mark.asyncio
async def test_upload_avatar_to_storage_integration(storage_bucket):
    """Test uploading an avatar to Firebase Storage with real storage."""
    # Upload the image
    public_url, storage_path = await upload_avatar_to_storage(
        SAMPLE_IMAGE, "image/jpeg", storage_bucket
    )

    try:
        # Verify the upload was successful
        assert public_url is not None
        assert storage_path is not None
        assert storage_path.startswith("avatars/")
        assert storage_path.endswith(".jpeg")

        # Verify the blob exists
        blob = storage_bucket.blob(storage_path)
        assert blob.exists()

        # Verify the content
        downloaded_data = blob.download_as_bytes()
        assert downloaded_data == SAMPLE_IMAGE

    finally:
        # Clean up - delete the test blob
        if storage_path:
            blob = storage_bucket.blob(storage_path)
            if blob.exists():
                blob.delete()


@pytest.mark.asyncio
async def test_handle_avatar_url_integration(storage_bucket):
    """Test handling a data URI avatar with real storage."""
    # Process the data URI
    public_url, storage_path = await handle_avatar_url(SAMPLE_DATA_URI, storage_bucket)

    try:
        # Verify the upload was successful
        assert public_url is not None
        assert storage_path is not None
        assert storage_path.startswith("avatars/")
        assert storage_path.endswith(".jpeg")

        # Verify the blob exists
        blob = storage_bucket.blob(storage_path)
        assert blob.exists()

        # Verify the content
        downloaded_data = blob.download_as_bytes()
        assert downloaded_data == SAMPLE_IMAGE

    finally:
        # Clean up - delete the test blob
        if storage_path:
            blob = storage_bucket.blob(storage_path)
            if blob.exists():
                blob.delete()


@pytest.mark.asyncio
async def test_handle_avatar_url_cleanup_integration(storage_bucket):
    """Test that multiple uploads of the same image reuse the same blob."""
    # Upload the same image twice
    public_url1, storage_path1 = await handle_avatar_url(
        SAMPLE_DATA_URI, storage_bucket
    )
    public_url2, storage_path2 = await handle_avatar_url(
        SAMPLE_DATA_URI, storage_bucket
    )

    try:
        # Verify both uploads returned the same path
        assert storage_path1 == storage_path2
        assert public_url1 == public_url2

        # Verify only one blob exists
        blob = storage_bucket.blob(storage_path1)
        assert blob.exists()

    finally:
        # Clean up - delete the test blob
        if storage_path1:
            blob = storage_bucket.blob(storage_path1)
            if blob.exists():
                blob.delete()
