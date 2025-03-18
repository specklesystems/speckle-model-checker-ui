from firebase_functions import https_fn
import firebase_admin
from firebase_admin import auth, firestore
from jinja2 import Template
import json
import uuid
import datetime
import requests
from ..utils.jinja_env import render_template
from flask import make_response

import os


# Get Speckle configuration from environment
def get_speckle_config():
    """Get Speckle application configuration from Firebase config."""
    try:

        return {
            "app_id": os.environ.get("SPECKLE_APP_ID"),
            "app_secret": os.environ.get("SPECKLE_APP_SECRET"),
            "server_url": os.environ.get(
                "SPECKLE_SERVER_URL", "https://app.speckle.systems"
            ),
        }
    except Exception as e:
        print(f"Error getting Speckle config: {str(e)}")
        return {
            "app_id": None,
            "app_secret": None,
            "server_url": "https://app.speckle.systems",
        }


def init_speckle_auth(request):
    """Initialize Speckle authentication and return a login URL."""

    try:
        speckle_config = get_speckle_config()
        app_id = os.environ.get("SPECKLE_APP_ID")
        server_url = os.environ.get("SPECKLE_SERVER_URL", "https://app.speckle.systems")
        challenge_id = os.environ.get("SPECKLE_CHALLENGE_ID")

        if not app_id:
            return https_fn.Response(
                json.dumps({"error": "Speckle App ID is not configured"}),
                mimetype="application/json",
                status=500,
            )

        # Build authentication URL
        host_url = (
            request.host_url
            if hasattr(request, "host_url")
            else request.headers.get("Host", "")
        )
        if not host_url.startswith("http"):
            protocol = "https" if not host_url.startswith("localhost") else "http"
            host_url = f"{protocol}://{host_url}/"

        base_url = host_url.rstrip("/")
        redirect_url = f"{base_url}/auth-callback.html"
        auth_url = f"{server_url}/authn/verify/{app_id}/{challenge_id}?redirectUrl={redirect_url}"

        return https_fn.Response(
            json.dumps({"challengeId": challenge_id, "authUrl": auth_url}),
            mimetype="application/json",
        )
    except Exception as e:
        print(f"Auth initialization error: {str(e)}")
        return https_fn.Response(
            json.dumps({"error": str(e)}), mimetype="application/json", status=500
        )


def exchange_token(request):
    """Exchange Speckle access code for a Firebase custom token."""
    try:
        # Retrieve the challenge ID from the cookie
        challenge_id = os.environ.get("SPECKLE_CHALLENGE_ID")

        if not request.args:
            return https_fn.Response(
                json.dumps({"error": "No request data provided"}),
                mimetype="application/json",
                status=400,
            )

        # Retrieve accessCode request_args
        access_code = request.args.get("access_code")

        authenticated = False

        if not access_code or not challenge_id:
            return https_fn.Response(
                json.dumps({"error": "Missing access code or challenge ID"}),
                mimetype="application/json",
                status=400,
            )

        # Verify challenge exists and hasn't been used
        db = firestore.client()

        # Exchange access code for Speckle token
        speckle_config = get_speckle_config()
        app_id = os.environ.get("SPECKLE_APP_ID")
        app_secret = os.environ.get("SPECKLE_APP_SECRET")
        server_url = os.environ.get("SPECKLE_SERVER_URL", "https://app.speckle.systems")

        print(f"Access code: {access_code}")
        print(f"Challenge ID: {challenge_id}")

        token_exchange_url = f"{server_url}/auth/token"
        token_payload = {
            "accessCode": access_code,
            "appId": app_id,
            "appSecret": app_secret,
            "challenge": challenge_id,
        }

        token_response = requests.post(token_exchange_url, json=token_payload)

        if token_response.status_code != 200:
            return https_fn.Response(
                json.dumps(
                    {
                        "error": f"Failed to exchange token: {token_response.reason} ({token_response.status_code}) {json.loads(token_response.text)['err']}"
                    }
                ),
                mimetype="application/json",
                status=token_response.status_code,
            )
        else:
            authenticated = True

        token_data = token_response.json()

        print(f"Token data: {token_data}")

        # Get user profile from Speckle
        speckle_token = token_data["token"]
        refresh_token = token_data["refreshToken"]
        user_profile_url = f"{server_url}/graphql"

        profile_query = """
        query {
          activeUser {
            id
            name
            email
            avatar
          }
        }
        """

        profile_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {speckle_token}",
        }

        profile_response = requests.post(
            user_profile_url, headers=profile_headers, json={"query": profile_query}
        )

        if profile_response.status_code != 200:
            return https_fn.Response(
                json.dumps({"error": "Failed to get user profile"}),
                mimetype="application/json",
                status=profile_response.status_code,
            )

        profile_data = profile_response.json()
        user_data = profile_data["data"]["activeUser"]

        print(f"User data: {user_data}")
        print(f"Profile data: {profile_data}")

        # Create or update Firebase user
        try:
            firebase_user = auth.get_user_by_email(user_data["email"])

            # User exists, update properties if needed
            if (
                firebase_user.display_name != user_data["name"]
                or firebase_user.photo_url != user_data["avatar"]
            ):
                auth.update_user(
                    firebase_user.uid,
                    display_name=user_data["name"],
                    photo_url=user_data["avatar"],
                )

        except auth.UserNotFoundError:
            # Create new user
            firebase_user = auth.create_user(
                email=user_data["email"],
                display_name=user_data["name"],
                photo_url=user_data["avatar"],
            )

        # Store Speckle tokens in Firestore
        db.collection("userTokens").document(firebase_user.uid).set(
            {
                "speckleId": user_data["id"],
                "speckleToken": token_data["token"],
                "speckleRefreshToken": token_data["refreshToken"],
                "updatedAt": firestore.SERVER_TIMESTAMP,
            }
        )

        # Create Firebase custom token
        ## add a user claim to link the firebase id with the speckle id and token
        custom_token = auth.create_custom_token(
            firebase_user.uid, {"speckleId": user_data["id"]}
        )

        # Ensure it's a proper string (not bytes)
        custom_token_str = custom_token.decode() if isinstance(custom_token, bytes) else custom_token

        # Check if running locally in Firebase Emulator
        IS_FIREBASE_EMULATOR = os.environ.get("FUNCTIONS_EMULATOR") == "true"

        if IS_FIREBASE_EMULATOR:
            FIREBASE_HOSTING_URL = "http://127.0.0.1:5000"  # Firebase Hosting Emulator
            FIREBASE_FUNCTIONS_URL = "http://127.0.0.1:5001/{}/us-central1".format(
                os.environ.get("GCLOUD_PROJECT")
            )
        else:
            FIREBASE_HOSTING_URL = f"https://{os.environ.get('GCLOUD_PROJECT')}.web.app"
            FIREBASE_FUNCTIONS_URL = f"https://us-central1-{os.environ.get('GCLOUD_PROJECT')}.cloudfunctions.net"

        # Redirect URL for authentication callback
        redirect_url = f"{FIREBASE_HOSTING_URL}?authenticated={authenticated}&firebaseToken={custom_token_str}"


        print(f"Custom token: {custom_token} {custom_token_str}")


        return https_fn.Response(
            status=302,
            headers={"Location": redirect_url},
        )
    except Exception as e:
        print(f"Token exchange error: {str(e)}")
        return https_fn.Response(
            json.dumps({"error": str(e)}), mimetype="application/json", status=500
        )
