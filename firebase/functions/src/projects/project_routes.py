from firebase_functions import https_fn
from google.cloud import firestore

from ..utils.firestore_utils import (
    get_rules_for_ruleset,
    get_rulesets_for_project,
    get_speckle_token_for_user,
    safe_verify_id_token,
)
from ..utils.jinja_env import render_template
from ..utils.speckle_api import get_project_details, get_user_projects

db = firestore.Client()


def get_user_projects_view(request):
    """Return HTML for the user's Speckle projects."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return https_fn.Response(
            render_template("error.html", message="Unauthorized"),
            mimetype="text/html",
            status=401,
        )

    id_token = auth_header.split("Bearer ")[1]

    try:
        decoded_token = safe_verify_id_token(id_token)
        user_id = decoded_token["uid"]

        # Get speckle token from firestore
        speckle_token = get_speckle_token_for_user(user_id)

        if not speckle_token:
            return https_fn.Response(
                render_template(
                    "error.html",
                    message="Unable to access your Speckle token. Please sign out and sign in again.",
                ),
                mimetype="text/html",
            )

        # IMPORTANT: Call the function to get the projects data
        # The function get_user_projects should return the actual project data, not another function
        projects = get_user_projects(speckle_token)

        # Return the rendered template with the projects data
        return https_fn.Response(
            render_template("index.html", projects=projects),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading projects: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_location(request):
    """
    Get the base URL of the application for generating shared links.
    Returns the main hosting URL rather than the Cloud Function URL.
    """
    # Get project ID from environment
    import os

    project_id = os.environ.get("GCLOUD_PROJECT", "speckle-model-checker")

    # Check if running in emulator mode
    if (
        "FUNCTIONS_EMULATOR" in os.environ
        and os.environ.get("FUNCTIONS_EMULATOR") == "true"
    ):
        # Extract host without port from header
        host_url = request.headers.get("Host", "localhost:5000")
        if ":" in host_url:
            # Force the port to 5000 (hosting emulator) instead of function emulator port
            base_host = host_url.split(":")[0]
            host_url = f"{base_host}:5000"
        return f"http://{host_url}"

    # In production, use the Firebase Hosting URL instead of the Cloud Function URL
    return f"https://{project_id}.web.app"


def get_project_with_rulesets(request):
    """Return HTML for a project with its rulesets."""

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return https_fn.Response(
            render_template("error.html", message="Unauthorized"),
            mimetype="text/html",
            status=401,
        )

    id_token = auth_header.split("Bearer ")[1]

    # Extract project_id from path or query parameters
    project_id = None
    if "/projects/" in request.path:
        project_id = request.path.split("/projects/")[1].split("/")[0]
    else:
        project_id = request.args.get("projectId")

    if not project_id:
        return https_fn.Response(
            render_template("error.html", message="Missing project ID"),
            mimetype="text/html",
            status=400,
        )

    try:
        decoded_token = safe_verify_id_token(id_token)
        user_id = decoded_token["uid"]

        # Get speckle token
        speckle_token = get_speckle_token_for_user(user_id)

        if not speckle_token:
            return https_fn.Response(
                render_template(
                    "error.html",
                    message="Unable to access your Speckle token. Please sign out and sign in again.",
                ),
                mimetype="text/html",
            )

        # Fetch rulesets for this project
        rulesets = get_rulesets_for_project(user_id, project_id)

        # Fetch minimal project details
        project = get_project_details(speckle_token, project_id)

        def custom_serializer(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            return str(obj)  # fallback

        for ruleset in rulesets:
            ruleset["rules"] = get_rules_for_ruleset(ruleset["id"])

        location_origin = get_location(request)

        # Return the rendered template
        return https_fn.Response(
            render_template(
                "project_details.html",
                location_origin=location_origin,
                project=project,
                rulesets=rulesets,
            ),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading project: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_new_ruleset_form(request):
    """Return HTML for creating a new ruleset."""
    try:
        # Get project ID from query string
        project_id = request.args.get("projectId")

        if not project_id:
            return https_fn.Response(
                render_template("error.html", message="Missing project ID"),
                mimetype="text/html",
                status=400,
            )

        # Get auth header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                render_template("error.html", message="Unauthorized"),
                mimetype="text/html",
                status=401,
            )

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = safe_verify_id_token(id_token)
        user_id = decoded_token["uid"]

        # Get Speckle token
        speckle_token = get_speckle_token_for_user(user_id)
        if not speckle_token:
            return https_fn.Response(
                render_template(
                    "error.html", message="Unable to access your Speckle token"
                ),
                mimetype="text/html",
                status=401,
            )

        # Get project details to show the name
        project = get_project_details(speckle_token, project_id)
        if not project:
            return https_fn.Response(
                render_template("error.html", message="Project not found"),
                mimetype="text/html",
                status=404,
            )

        # Return the form
        return https_fn.Response(
            render_template(
                "new_ruleset_form.html",
                project_id=project_id,
                project_name=project["name"],
            ),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading form: {str(e)}"),
            mimetype="text/html",
            status=500,
        )
