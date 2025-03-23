from firebase_functions import https_fn
from google.cloud import firestore

from ..utils.firestore_utils import (
    create_ruleset,
    delete_ruleset,
    get_rules_for_ruleset,
    get_ruleset,
    safe_verify_id_token,
    update_ruleset,
)
from ..utils.jinja_env import render_template


# Get Speckle token for a user from Firestore
def get_speckle_token_for_user(user_id):
    """Get the Speckle token for a user from Firestore."""
    db = firestore.client()

    try:
        user_token_doc = db.collection("userTokens").document(user_id).get()
        if user_token_doc.exists:
            return user_token_doc.to_dict().get("speckleToken")
        return None
    except Exception:
        return None


def get_ruleset_edit_form(request, ruleset_id):
    """Return HTML for editing a ruleset."""
    try:
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

        # Get the ruleset
        ruleset = get_ruleset(ruleset_id)

        if not ruleset:
            return https_fn.Response(
                render_template("error.html", message="Ruleset not found"),
                mimetype="text/html",
                status=404,
            )

        # Verify ownership
        if ruleset.get("userId") != user_id:
            return https_fn.Response(
                render_template(
                    "error.html",
                    message="You don't have permission to edit this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Get rules for this ruleset
        rules = get_rules_for_ruleset(ruleset_id)

        # Return the template with both ruleset and rules
        return https_fn.Response(
            render_template(
                "edit_ruleset.html",
                ruleset=ruleset,
                rules=rules,
                ruleset_id=ruleset_id,
            ),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading ruleset: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def create_new_ruleset(request):
    """Create a new ruleset."""
    try:
        # Get form data
        form_data = request.form
        project_id = form_data.get("projectId")
        name = form_data.get("name")
        description = form_data.get("description", "")

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

        if not project_id or not name:
            return https_fn.Response(
                render_template("error.html", message="Missing required fields"),
                mimetype="text/html",
                status=400,
            )

        # Create the ruleset
        ruleset = create_ruleset(user_id, project_id, name, description)

        # Redirect to the project page
        return https_fn.Response(
            render_template("edit_ruleset.html", ruleset=ruleset),
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error creating ruleset: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def update_ruleset_info(request, ruleset_id):
    """Update a ruleset's basic information."""
    try:
        # Get form data
        form_data = request.form
        name = form_data.get("name")
        description = form_data.get("description", "")

        if not name:
            return https_fn.Response(
                render_template("error.html", message="Missing required fields"),
                mimetype="text/html",
                status=400,
            )

        # Get user info from request
        user_id = request.user_id

        # Get current ruleset to verify ownership
        ruleset = get_ruleset(ruleset_id)

        if not ruleset:
            return https_fn.Response(
                render_template("error.html", message="Ruleset not found"),
                mimetype="text/html",
                status=404,
            )

        # Verify ownership
        if ruleset.get("userId") != user_id:
            return https_fn.Response(
                render_template(
                    "error.html",
                    message="You don't have permission to edit this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Update the ruleset
        update_ruleset(ruleset_id, {"name": name, "description": description})

        # Reload the edit page
        return get_ruleset_edit_form(request, ruleset_id)

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error updating ruleset: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def delete_ruleset_handler(request, ruleset_id):
    """Delete a ruleset."""

    try:
        # Get auth header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return https_fn.Response(
                render_template("error.html", message="Unauthorized"),
                mimetype="text/html",
                status=401,
            )

        # request should be a DELETE request
        if request.method != "DELETE":
            return https_fn.Response(
                render_template("error.html", message="Invalid request method"),
                mimetype="text/html",
                status=405,
            )

        id_token = auth_header.split("Bearer ")[1]
        decoded_token = safe_verify_id_token(id_token)
        user_id = decoded_token["uid"]

        # Get current ruleset to verify ownership and get project ID
        ruleset = get_ruleset(ruleset_id)

        if not ruleset:
            return https_fn.Response(
                render_template("error.html", message="Ruleset not found"),
                mimetype="text/html",
                status=404,
            )

        # Verify ownership
        if ruleset.get("userId") != user_id:
            return https_fn.Response(
                render_template(
                    "error.html",
                    message="You don't have permission to delete this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Delete the ruleset
        delete_ruleset(ruleset_id)

        # Return empty response
        return https_fn.Response("", status=204)

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error deleting ruleset: {str(e)}"),
            mimetype="text/html",
            status=500,
        )
