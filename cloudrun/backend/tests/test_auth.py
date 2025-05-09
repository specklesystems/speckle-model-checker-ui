import base64
from unittest.mock import Mock

import pytest
from auth import handle_avatar_url, upload_avatar_to_storage

# Sample test data
SAMPLE_IMAGE = b"fake image data"
SAMPLE_BASE64 = base64.b64encode(SAMPLE_IMAGE).decode()
SAMPLE_DATA_URI = f"data:image/jpeg;base64,{SAMPLE_BASE64}"
SAMPLE_STORAGE_PATH = "avatars/1234567890abcdef.jpeg"
SAMPLE_PUBLIC_URL = "https://storage.googleapis.com/speckle-model-checker.firebasestorage.app/avatars/1234567890abcdef.jpeg"


@pytest.fixture
def mock_storage_bucket():
    mock_bucket = Mock()
    mock_blob = Mock()
    mock_blob.public_url = SAMPLE_PUBLIC_URL
    mock_bucket.blob.return_value = mock_blob
    return mock_bucket


@pytest.mark.asyncio
async def test_upload_avatar_to_storage(mock_storage_bucket):
    """Test uploading an avatar to Firebase Storage"""
    public_url, storage_path = await upload_avatar_to_storage(
        SAMPLE_IMAGE, "image/jpeg", mock_storage_bucket
    )

    # Verify the blob was created and uploaded
    mock_storage_bucket.blob.assert_called_once()
    mock_blob = mock_storage_bucket.blob.return_value
    mock_blob.upload_from_string.assert_called_once_with(
        SAMPLE_IMAGE, content_type="image/jpeg"
    )
    mock_blob.make_public.assert_called_once()

    # Verify the returned values
    assert public_url == SAMPLE_PUBLIC_URL
    assert storage_path.startswith("avatars/")
    assert storage_path.endswith(".jpeg")


@pytest.mark.asyncio
async def test_handle_avatar_url_with_data_uri(mock_storage_bucket):
    """Test handling a data URI avatar"""
    public_url, storage_path = await handle_avatar_url(
        SAMPLE_DATA_URI, mock_storage_bucket
    )

    # Verify the upload was called
    mock_storage_bucket.blob.assert_called_once()
    mock_blob = mock_storage_bucket.blob.return_value
    mock_blob.upload_from_string.assert_called_once()

    # Verify the returned values
    assert public_url == SAMPLE_PUBLIC_URL
    assert storage_path.startswith("avatars/")
    assert storage_path.endswith(".jpeg")


@pytest.mark.asyncio
async def test_handle_avatar_url_with_regular_url():
    """Test handling a regular URL avatar"""
    regular_url = "https://example.com/avatar.jpg"
    public_url, storage_path = await handle_avatar_url(regular_url)

    # Should return the original URL and no storage path
    assert public_url == regular_url
    assert storage_path is None


@pytest.mark.asyncio
async def test_handle_avatar_url_with_none():
    """Test handling no avatar URL"""
    public_url, storage_path = await handle_avatar_url(None)

    # Should return None for both values
    assert public_url is None
    assert storage_path is None
