import os
from unittest.mock import Mock, patch

import pytest
from auth import exchange_token, init_auth
from fastapi import Request
from firebase_admin import auth
from starlette.datastructures import QueryParams


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request with session support."""
    request = Mock(spec=Request)
    request.session = {}
    request.query_params = QueryParams({})
    return request


@pytest.fixture
def mock_speckle_user():
    """Sample Speckle user data."""
    return {
        "id": "test-user-id",
        "name": "Test User",
        "email": "test@example.com",
        "avatar": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",  # Minimal valid base64
    }


@pytest.fixture
def mock_speckle_response():
    """Mock Speckle API responses."""
    return {
        "token": "test-token",
        "refreshToken": "test-refresh-token",
        "data": {
            "activeUser": {
                "id": "test-user-id",
                "name": "Test User",
                "email": "test@example.com",
                "avatar": "data:image/jpeg;base64,/9j/4AAQSkZJRg==",
            }
        },
    }


@pytest.mark.asyncio
async def test_init_auth(mock_request):
    """Test initialization of authentication."""
    with patch.dict(
        os.environ,
        {
            "SPECKLE_APP_ID": "test-app-id",
            "SPECKLE_APP_SECRET": "test-app-secret",
            "SPECKLE_SERVER_URL": "https://test.speckle.systems",
        },
    ):
        response = await init_auth(mock_request)

        # Verify response structure
        assert response.status_code == 200
        data = response.body.decode()
        assert "challengeId" in data
        assert "authUrl" in data
        assert "test-app-id" in data

        # Verify session was set
        assert "speckle_challenge_id" in mock_request.session


@pytest.mark.asyncio
async def test_exchange_token_new_user(
    mock_request, mock_speckle_user, mock_speckle_response
):
    """Test token exchange with new user creation."""
    # Setup mocks
    mock_request.query_params = QueryParams({"access_code": "test-code"})
    mock_request.session["speckle_challenge_id"] = "test-challenge"

    # Mock Speckle API responses
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: mock_speckle_response),
            Mock(
                status_code=200,
                json=lambda: {"data": {"activeUser": mock_speckle_user}},
            ),
        ]

        # Mock Firebase auth
        with patch("firebase_admin.auth") as mock_auth:
            # Simulate user not found
            mock_auth.get_user_by_email.side_effect = auth.UserNotFoundError(
                "User not found"
            )

            # Mock user creation
            mock_user = Mock()
            mock_user.uid = "test-user-id"
            mock_user.email = mock_speckle_user["email"]
            mock_user.display_name = mock_speckle_user["name"]
            mock_user.photo_url = None
            mock_auth.create_user.return_value = mock_user

            # Mock custom token creation
            mock_auth.create_custom_token.return_value = Mock(
                decode=lambda: "test-firebase-token"
            )

            # Execute
            response = await exchange_token(mock_request)

            # Verify user creation
            mock_auth.create_user.assert_called_once_with(
                email=mock_speckle_user["email"],
                display_name=mock_speckle_user["name"],
                photo_url=None,
                uid=mock_speckle_user["id"],
            )

            # Verify custom claims were set
            mock_auth.set_custom_user_claims.assert_called_once()

            # Verify response
            assert response.status_code == 303
            assert "authenticated=True" in response.headers["location"]
            assert "ft=test-firebase-token" in response.headers["location"]


@pytest.mark.asyncio
async def test_exchange_token_existing_user(
    mock_request, mock_speckle_user, mock_speckle_response
):
    """Test token exchange with existing user update."""
    # Setup mocks
    mock_request.query_params = QueryParams({"access_code": "test-code"})
    mock_request.session["speckle_challenge_id"] = "test-challenge"

    # Mock Speckle API responses
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = [
            Mock(status_code=200, json=lambda: mock_speckle_response),
            Mock(
                status_code=200,
                json=lambda: {"data": {"activeUser": mock_speckle_user}},
            ),
        ]

        # Mock Firebase auth
        with patch("firebase_admin.auth") as mock_auth:
            # Mock existing user
            mock_user = Mock()
            mock_user.uid = "test-user-id"
            mock_user.email = mock_speckle_user["email"]
            mock_user.display_name = mock_speckle_user["name"]
            mock_user.photo_url = None
            mock_user.custom_claims = {}
            mock_auth.get_user_by_email.return_value = mock_user

            # Mock custom token creation
            mock_auth.create_custom_token.return_value = Mock(
                decode=lambda: "test-firebase-token"
            )

            # Execute
            response = await exchange_token(mock_request)

            # Verify user was not created
            mock_auth.create_user.assert_not_called()

            # Verify user was updated
            mock_auth.update_user.assert_called_once()

            # Verify custom claims were updated
            mock_auth.set_custom_user_claims.assert_called_once()

            # Verify response
            assert response.status_code == 303
            assert "authenticated=True" in response.headers["location"]
            assert "ft=test-firebase-token" in response.headers["location"]


@pytest.mark.asyncio
async def test_exchange_token_missing_params(mock_request):
    """Test token exchange with missing parameters."""
    # Setup mocks with missing access code
    mock_request.query_params = QueryParams({})
    mock_request.session["speckle_challenge_id"] = "test-challenge"

    # Execute and verify error
    with pytest.raises(Exception) as exc_info:
        await exchange_token(mock_request)
    assert "Missing access code or challenge ID" in str(exc_info.value)


@pytest.mark.asyncio
async def test_exchange_token_speckle_error(mock_request):
    """Test token exchange with Speckle API error."""
    # Setup mocks
    mock_request.query_params = QueryParams({"access_code": "test-code"})
    mock_request.session["speckle_challenge_id"] = "test-challenge"

    # Mock Speckle API error
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = Mock(status_code=400, text="Invalid code")

        # Execute and verify error
        with pytest.raises(Exception) as exc_info:
            await exchange_token(mock_request)
        assert "Failed to exchange token" in str(exc_info.value)
