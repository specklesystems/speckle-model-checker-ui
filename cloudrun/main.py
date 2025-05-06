# cloudrun/main.py - Main Flask Application
import os
from flask import Flask, request, render_template, send_file, make_response, jsonify
import firebase_admin
from firebase_admin import firestore
import logging

# Import our modules
from src.routes import setup_routes
from src.utils import render_template

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder="public")

# Configure session
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24).hex())
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_session/"
app.config["SESSION_PERMANENT"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

# Initialize Firebase
try:
    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    db = firestore.Client()

    # Add database to app context for easy access
    app.db = db
except Exception as e:
    logger.error(f"Firebase initialization error: {str(e)}")
    # We'll continue without Firebase and handle errors in routes

# Make environment variables easily accessible
app.env = {
    "SPECKLE_APP_ID": os.environ.get("SPECKLE_APP_ID"),
    "SPECKLE_APP_SECRET": os.environ.get("SPECKLE_APP_SECRET"),
    "SPECKLE_CHALLENGE_ID": os.environ.get("SPECKLE_CHALLENGE_ID"),
    "SPECKLE_SERVER_URL": os.environ.get(
        "SPECKLE_SERVER_URL", "https://app.speckle.systems"
    ),
}

# Setup all routes
setup_routes(app)


# Health check
@app.route("/_health")
def health():
    # Check Firebase connection
    try:
        # Simple read operation to test Firestore connection
        app.db.collection("health").document("check").get()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify(
        {
            "status": "healthy",
            "firebase": db_status,
            "env_configured": all(
                [app.env["SPECKLE_APP_ID"], app.env["SPECKLE_APP_SECRET"]]
            ),
        }
    )


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return (
        render_template(
            "error.html",
            message="Internal server error",
            debug_info=str(error) if app.debug else None,
        ),
        500,
    )


# Handle CORS for local development
@app.after_request
def add_cors_headers(response):
    # Only in development mode
    if os.environ.get("FLASK_ENV") == "development":
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type,Authorization"
        )
        response.headers.add(
            "Access-Control-Allow-Methods", "GET,PUT,POST,DELETE,PATCH"
        )
    return response


# Run the app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Log startup information
    logger.info(f"Starting Speckle Model Checker on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Speckle Server URL: {app.env['SPECKLE_SERVER_URL']}")

    # Start the Flask application
    app.run(host="0.0.0.0", port=port, debug=debug)
