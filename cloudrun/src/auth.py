# cloudrun/src/auth.py - Authentication Functions
import os
import secrets
import requests
from flask import jsonify, make_response, session, redirect, url_for
from firebase_admin import auth
from google.cloud import firestore


def init_auth(app):
    """Initialize Speckle authentication"""
    app_id = app.env["SPECKLE_APP_ID"]
    app_secret = app.env["SPECKLE_APP_SECRET"]

    if not app_id or not app_secret:
        return jsonify({"error": "Speckle App ID or Secret not configured"}), 500

    # Generate challenge ID and store in session
    challenge_id = secrets.token_urlsafe(32)
    session["speckle_challenge_id"] = challenge_id

    auth_url = f"{app.env['SPECKLE_SERVER_URL']}/authn/verify/{app_id}/{challenge_id}"

    return jsonify(
        {
            "challengeId": challenge_id,
            "authUrl": auth_url,
            "appId": app_id,
            "appSecret": app_secret,
        }
    )


def exchange_token(app, request):
    """Exchange token - using session for challenge ID"""
    access_code = request.args.get("access_code")
    challenge_id = session.pop(
        "speckle_challenge_id", None
    )  # Get and remove from session

    if not access_code or not challenge_id:
        return jsonify({"error": "Missing access code or challenge ID"}), 400

    # Exchange code for token
    token_response = requests.post(
        f"{app.env['SPECKLE_SERVER_URL']}/auth/token",
        json={
            "accessCode": access_code,
            "appId": app.env["SPECKLE_APP_ID"],
            "appSecret": app.env["SPECKLE_APP_SECRET"],
            "challenge": challenge_id,
        },
    )

    if token_response.status_code != 200:
        return (
            jsonify({"error": "Failed to exchange token"}),
            token_response.status_code,
        )

    data = token_response.json()
    speckle_token = data["token"]
    refresh_token = data.get("refreshToken", "")

    # Get user profile
    profile_response = requests.post(
        f"{app.env['SPECKLE_SERVER_URL']}/graphql",
        headers={"Authorization": f"Bearer {speckle_token}"},
        json={"query": "query { activeUser { id name email avatar } }"},
    )

    if profile_response.status_code != 200:
        return jsonify({"error": "Failed to get user profile"}), 500

    user_data = profile_response.json()["data"]["activeUser"]

    # Create/update Firebase user
    firebase_user = create_or_update_firebase_user(user_data)

    # Store tokens both in session and Firestore
    session["speckle_id"] = user_data["id"]
    session["speckle_token"] = speckle_token
    session["firebase_uid"] = firebase_user.uid

    # Store token in Firestore
    app.db.collection("userTokens").document(firebase_user.uid).set(
        {
            "speckleId": user_data["id"],
            "speckleToken": speckle_token,
            "speckleRefreshToken": refresh_token,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }
    )

    # Create custom token for client-side Firebase auth
    custom_token = auth.create_custom_token(firebase_user.uid)

    # Redirect to main page with auth success
    return redirect(url_for("index", authenticated="True", ft=custom_token.decode()))


def create_or_update_firebase_user(user):
    """Create or update Firebase user"""
    try:
        firebase_user = auth.get_user_by_email(user["email"])
        # Update if needed
        if (
            firebase_user.display_name != user["name"]
            or firebase_user.photo_url != user["avatar"]
        ):
            auth.update_user(
                firebase_user.uid,
                display_name=user["name"],
                photo_url=user["avatar"],
            )
    except auth.UserNotFoundError:
        firebase_user = auth.create_user(
            email=user["email"],
            display_name=user["name"],
            photo_url=user["avatar"],
            password=os.urandom(20).hex(),
        )
    return firebase_user


def verify_session(app):
    """Verify user session - returns user_id if valid"""
    firebase_uid = session.get("firebase_uid")
    if not firebase_uid:
        return None
    return firebase_uid


def verify_token(app, id_token):
    """Verify Firebase ID token and return user ID"""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token["uid"]
    except Exception as e:
        print(f"Token verification error: {str(e)}")
        return None


def get_user_token(app, user_id):
    """Get Speckle token from session or Firestore"""
    # Try session first for performance
    if session.get("firebase_uid") == user_id:
        speckle_token = session.get("speckle_token")
        if speckle_token:
            return speckle_token

    # Fallback to Firestore
    user_token_doc = app.db.collection("userTokens").document(user_id).get()
    if not user_token_doc.exists:
        return None
    return user_token_doc.to_dict().get("speckleToken")
