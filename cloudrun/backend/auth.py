from fastapi import HTTPException, Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.config import Config
import firebase_admin
from firebase_admin import auth, credentials, firestore
import os
from dotenv import load_dotenv
import secrets
import httpx
from urllib.parse import urljoin

load_dotenv()


# Initialize Firebase Admin SDK
def initialize_firebase():
    cred_path = "/workspaces/speckle_model_checker/firebase-service-account-key.json"
    if not os.path.exists(cred_path):
        raise ValueError("Firebase credentials file not found at: " + cred_path)

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        raise ValueError(f"Failed to initialize Firebase: {str(e)}")


initialize_firebase()
db = firestore.client()


async def init_auth(request: Request):
    """Initialize Speckle authentication"""
    app_id = os.getenv("SPECKLE_APP_ID")
    app_secret = os.getenv("SPECKLE_APP_SECRET")
    server_url = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")

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


async def exchange_token(request: Request):
    """Exchange token - using session for challenge ID"""
    access_code = request.query_params.get("access_code")
    challenge_id = request.session.pop("speckle_challenge_id", None)
    server_url = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")

    if not access_code or not challenge_id:
        raise HTTPException(
            status_code=400, detail="Missing access code or challenge ID"
        )

    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_response = await client.post(
            urljoin(server_url, "/auth/token"),
            json={
                "accessCode": access_code,
                "appId": os.getenv("SPECKLE_APP_ID"),
                "appSecret": os.getenv("SPECKLE_APP_SECRET"),
                "challenge": challenge_id,
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=token_response.status_code,
                detail="Failed to exchange token",
            )

        data = token_response.json()
        speckle_token = data["token"]
        refresh_token = data.get("refreshToken", "")

        # Get user profile
        profile_response = await client.post(
            urljoin(server_url, "/graphql"),
            headers={"Authorization": f"Bearer {speckle_token}"},
            json={"query": "query { activeUser { id name email avatar } }"},
        )

        if profile_response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to get user profile")

        user_data = profile_response.json()["data"]["activeUser"]

        # Create/update Firebase user
        try:
            firebase_user = auth.get_user_by_email(user_data["email"])
        except:
            firebase_user = auth.create_user(
                email=user_data["email"],
                display_name=user_data["name"],
                photo_url=user_data["avatar"],
                uid=user_data["id"],
            )

        # Store tokens in session
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
        db.collection("userTokens").document(firebase_user.uid).set(
            {
                "speckleId": user_data["id"],
                "speckleToken": speckle_token,
                "speckleRefreshToken": refresh_token,
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )

        # Create custom token for client-side Firebase auth
        custom_token = auth.create_custom_token(firebase_user.uid)

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
