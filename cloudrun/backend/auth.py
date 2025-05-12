import base64
import hashlib
import json
import os
import secrets
from pathlib import Path
from urllib.parse import urljoin

import firebase_admin
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, Request
from firebase_admin import auth, credentials, firestore, storage
from starlette.responses import JSONResponse, RedirectResponse

load_dotenv()

# Create avatars directory if it doesn't exist
AVATARS_DIR = Path("./frontend/static/avatars")
AVATARS_DIR.mkdir(parents=True, exist_ok=True)


# Initialize Firebase Admin SDK
def initialize_firebase():
    cred_path = "./firebase-service-account-key.json"
    if not os.path.exists(cred_path):
        raise ValueError("Firebase credentials file not found at: " + cred_path)

    try:
        cred = credentials.Certificate(cred_path)
        app = firebase_admin.initialize_app(
            cred, {"storageBucket": "speckle-model-checker.firebasestorage.app"}
        )
        return app
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase: {str(e)}")


# Initialize Firebase only if not already initialized
try:
    app = firebase_admin.get_app()
except ValueError:
    app = initialize_firebase()

db = firestore.client()
bucket = storage.bucket()


async def init_auth(request: Request):
    print("Initializing Speckle authentication...")

    """Initialize Speckle authentication"""
    app_id = os.getenv("SPECKLE_APP_ID")
    app_secret = os.getenv("SPECKLE_APP_SECRET")
    server_url = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")

    print(f"App ID: {app_id}")
    print(f"App Secret: {app_secret}")
    print(f"Server URL: {server_url}")

    if not app_id or not app_secret:
        raise HTTPException(
            status_code=500, detail="Speckle App ID or Secret not configured"
        )

    # Generate challenge ID and store in session
    challenge_id = secrets.token_urlsafe(32)
    request.session["speckle_challenge_id"] = challenge_id

    auth_url = f"{server_url}/authn/verify/{app_id}/{challenge_id}"

    return JSONResponse(
        {
            "challengeId": challenge_id,
            "authUrl": auth_url,
            "appId": app_id,
            "appSecret": app_secret,
        }
    )


async def upload_avatar_to_storage(
    image_data: bytes, mime_type: str, storage_bucket=None
) -> tuple[str, str]:
    """Upload avatar image to Firebase Storage and return the public URL and storage path."""
    if storage_bucket is None:
        storage_bucket = bucket

    try:
        # Generate a unique filename
        file_hash = hashlib.md5(image_data).hexdigest()
        extension = mime_type.split("/")[-1]
        filename = f"avatars/{file_hash}.{extension}"

        # Create a blob and upload the file
        blob = storage_bucket.blob(filename)
        blob.upload_from_string(image_data, content_type=mime_type)

        # Make the file publicly accessible
        blob.make_public()

        # Return both the public URL and the storage path
        return blob.public_url, filename
    except Exception as e:
        print(f"Error uploading avatar to Firebase Storage: {str(e)}")
        return None, None


async def handle_avatar_url(avatar_url: str, storage_bucket=None) -> tuple[str, str]:
    """Handle avatar URL, converting data URIs to Firebase Storage URLs if needed.
    Returns a tuple of (public_url, storage_path)"""
    if not avatar_url:
        return None, None

    if not avatar_url.startswith("data:"):
        return avatar_url, None

    try:
        # Parse the data URI
        # Format: data:image/jpeg;base64,/9j/4AAQSkZJRg...
        header, encoded = avatar_url.split(",", 1)
        mime_type = header.split(";")[0].split(":")[1]

        # Decode base64
        image_data = base64.b64decode(encoded)

        # Upload to Firebase Storage
        storage_url, storage_path = await upload_avatar_to_storage(
            image_data, mime_type, storage_bucket
        )
        if storage_url:
            print(f"Successfully uploaded avatar to Firebase Storage: {storage_url}")
            return storage_url, storage_path
        else:
            print("Failed to upload avatar to Firebase Storage")
            return None, None

    except Exception as e:
        print(f"Error processing avatar data URI: {str(e)}")
        return None, None


async def exchange_token(request: Request):
    """Exchange token - using session for challenge ID"""
    print("=== Starting exchange_token function ===")

    access_code = request.query_params.get("access_code")
    challenge_id = request.session.pop("speckle_challenge_id", None)
    server_url = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")

    print(f"Access code: {access_code}")
    print(f"Challenge ID: {challenge_id}")
    print(f"Server URL: {server_url}")

    if not access_code or not challenge_id:
        print("Error: Missing access code or challenge ID")
        raise HTTPException(
            status_code=400, detail="Missing access code or challenge ID"
        )

    async with httpx.AsyncClient() as client:
        # Exchange code for token
        print("Exchanging code for token...")
        token_response = await client.post(
            urljoin(server_url, "/auth/token"),
            json={
                "accessCode": access_code,
                "appId": os.getenv("SPECKLE_APP_ID"),
                "appSecret": os.getenv("SPECKLE_APP_SECRET"),
                "challenge": challenge_id,
            },
        )

        print(f"Token response status: {token_response.status_code}")
        if token_response.status_code != 200:
            print(f"Error response from token exchange: {token_response.text}")
            raise HTTPException(
                status_code=token_response.status_code,
                detail="Failed to exchange token",
            )

        data = token_response.json()
        speckle_token = data["token"]
        refresh_token = data.get("refreshToken", "")
        print("Successfully obtained Speckle token")

        # Get user profile
        print("Fetching user profile...")
        profile_response = await client.post(
            urljoin(server_url, "/graphql"),
            headers={"Authorization": f"Bearer {speckle_token}"},
            json={"query": "query { activeUser { id name email avatar } }"},
        )

        print(f"Profile response status: {profile_response.status_code}")
        if profile_response.status_code != 200:
            print(f"Error response from profile fetch: {profile_response.text}")
            raise HTTPException(status_code=500, detail="Failed to get user profile")

        user_data = profile_response.json()["data"]["activeUser"]
        print(f"User data received: {json.dumps(user_data, indent=2)}")

        # Create/update Firebase user
        try:
            print(f"Attempting to get Firebase user by email: {user_data['email']}")
            firebase_user = auth.get_user_by_email(user_data["email"])
            print(f"Found existing Firebase user: {firebase_user.uid}")

            # Handle avatar URL and update custom claims
            photo_url, storage_path = await handle_avatar_url(
                user_data.get("avatar"), bucket
            )
            if photo_url:
                # Update user profile with new photo URL
                auth.update_user(firebase_user.uid, photo_url=photo_url)

                # Update custom claims with storage path
                current_claims = firebase_user.custom_claims or {}
                current_claims["avatarStoragePath"] = storage_path
                auth.set_custom_user_claims(firebase_user.uid, current_claims)
                print("Updated user profile and claims with new avatar")

        except Exception as e:
            print(f"User not found in Firebase, creating new user. Error: {str(e)}")
            try:
                # Handle avatar URL
                photo_url, storage_path = await handle_avatar_url(
                    user_data.get("avatar"), bucket
                )

                # Create user with initial custom claims
                custom_claims = (
                    {"avatarStoragePath": storage_path} if storage_path else {}
                )

                firebase_user = auth.create_user(
                    email=user_data["email"],
                    display_name=user_data["name"],
                    photo_url=photo_url,
                    uid=user_data["id"],
                )

                # Set custom claims after user creation
                if custom_claims:
                    auth.set_custom_user_claims(firebase_user.uid, custom_claims)

                print(f"Created new Firebase user: {firebase_user.uid}")
            except Exception as create_error:
                print(f"Error creating Firebase user: {str(create_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create Firebase user: {str(create_error)}",
                )

        # Store tokens in session
        print("Storing tokens in session...")
        request.session["speckle_id"] = user_data["id"]
        request.session["speckle_token"] = speckle_token
        request.session["firebase_uid"] = firebase_user.uid
        request.session["user"] = {
            "id": firebase_user.uid,
            "name": firebase_user.display_name,
            "email": firebase_user.email,
            "avatar": firebase_user.photo_url,
        }

        # Store token in Firestore
        print("Storing token in Firestore...")
        try:
            db.collection("userTokens").document(firebase_user.uid).set(
                {
                    "speckleId": user_data["id"],
                    "speckleToken": speckle_token,
                    "speckleRefreshToken": refresh_token,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )
            print("Successfully stored token in Firestore")
        except Exception as e:
            print(f"Error storing token in Firestore: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to store token in Firestore: {str(e)}"
            )

        # Create custom token for client-side Firebase auth
        print("Creating custom token for client-side auth...")
        try:
            custom_token = auth.create_custom_token(firebase_user.uid)
            print("Successfully created custom token")
        except Exception as e:
            print(f"Error creating custom token: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create custom token: {str(e)}"
            )

        print("=== Completed exchange_token function successfully ===")
        return RedirectResponse(
            url=f"/?authenticated=True&ft={custom_token.decode()}", status_code=303
        )


async def get_current_user(request: Request):
    """Get the current authenticated user from the session."""
    # First try to get user from session
    user = request.session.get("user")
    if user:
        return user

    # Fallback to checking speckle_id
    speckle_id = request.session.get("speckle_id")
    if not speckle_id:
        return None

    try:
        firebase_user = auth.get_user(speckle_id)
        user = {
            "id": firebase_user.uid,
            "name": firebase_user.display_name,
            "email": firebase_user.email,
            "avatar": firebase_user.photo_url,
        }
        # Update session with user data
        request.session["user"] = user
        return user
    except:
        return None
