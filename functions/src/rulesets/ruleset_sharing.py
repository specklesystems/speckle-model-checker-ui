from firebase_functions import https_fn
from io import StringIO
import csv

from ..projects.project_routes import get_location
from ..utils.firestore_utils import (
    get_rules_for_ruleset,
    get_ruleset,
    safe_verify_id_token,
    toggle_ruleset_sharing,
)
from ..utils.jinja_env import render_template


def get_share_dialog(request, ruleset_id):
    """Return HTML for the sharing dialog."""
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
                    message="You don't have permission to share this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        location_origin = get_location(request)

        # Return the dialog
        return https_fn.Response(
            render_template(
                "share_dialog.html",
                ruleset=ruleset,
                location_origin=location_origin,
            ),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template(
                "error.html", message=f"Error loading sharing dialog: {str(e)}"
            ),
            mimetype="text/html",
            status=500,
        )


def toggle_ruleset_sharing_handler(request, ruleset_id):
    """Toggle sharing status for a ruleset."""
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
                    message="You don't have permission to share this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Toggle sharing
        toggle_ruleset_sharing(ruleset_id)
        ruleset = get_ruleset(ruleset_id)
        ruleset["rules"] = get_rules_for_ruleset(ruleset["id"])

        # Get host URL for generating shared links
        host_url = request.headers.get("Host", "")
        if not host_url.startswith("http"):
            protocol = "https" if not host_url.startswith("localhost") else "http"
            location_origin = f"{protocol}://{host_url}"
        else:
            location_origin = host_url

        # Return the updated status
        return https_fn.Response(
            render_template(
                "ruleset_card.html",
                location_origin=location_origin,
                ruleset=ruleset,
            ),
            mimetype="text/html",
        )
    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error toggling sharing: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_shared_ruleset_view(request, ruleset_id):
    """Return TSV for a publicly shared ruleset."""
    try:
        # Get the ruleset
        ruleset = get_ruleset(ruleset_id)

        if not ruleset:
            return https_fn.Response(
                "Ruleset not found",
                mimetype="text/plain",
                status=404,
            )

        # Verify the ruleset is shared
        if not ruleset.get("isShared", False):
            return https_fn.Response(
                "This ruleset is not publicly shared",
                mimetype="text/plain",
                status=403,
            )

        # Get the rules
        rules = get_rules_for_ruleset(ruleset_id)
        ruleset["rules"] = rules

        # Generate TSV content
        tsv_content, filename = generate_ruleset_tsv(ruleset)

        # Create a proper filename using the ruleset name
        safe_name = ruleset.get("name", "ruleset").replace(" ", "_").lower()
        download_filename = f"{safe_name}.tsv"

        # Return TSV file directly - this is important for automation
        return https_fn.Response(
            tsv_content,
            mimetype="text/tab-separated-values",
            headers={
                "Content-Disposition": f'attachment; filename="{download_filename}"',
                "Content-Type": "text/tab-separated-values",
            },
        )
    except Exception as e:
        return https_fn.Response(
            f"Error serving shared ruleset: {str(e)}",
            mimetype="text/plain",
            status=500,
        )


def generate_ruleset_tsv(ruleset):
    """
    Generate TSV content for a ruleset.

    Args:
        ruleset (dict): Ruleset document with rules

    Returns:
        tuple: (tsv_content, filename)
    """
    # Generate TSV
    output = StringIO()
    writer = csv.writer(output, delimiter="\t")

    # Write header
    writer.writerow(
        [
            "Rule #",
            "Logic",
            "Property Path",
            "Predicate",
            "Value",
            "Severity",
            "Message",
        ]
    )

    # Write rules
    rule_number = 1
    for rule in ruleset.get("rules", []):
        # First condition row includes the rule number, severity, and message
        first_condition = True

        for condition in rule.get("conditions", []):
            row = []

            if first_condition:
                row.append(str(rule_number))  # Rule number
                first_condition = False
            else:
                row.append("")  # Empty rule number for additional conditions

            row.append(condition.get("logic", ""))  # Logic
            row.append(condition.get("propertyName", ""))  # Property Path
            row.append(condition.get("predicate", ""))  # Predicate
            row.append(condition.get("value", ""))  # Value

            if first_condition:
                row.append(rule.get("severity", "Error"))  # Severity
                row.append(rule.get("message", ""))  # Message
            else:
                row.append("")  # Empty severity for additional conditions
                row.append("")  # Empty message for additional conditions

            writer.writerow(row)

        rule_number += 1

    # Create filename based on ruleset name
    filename = f"{ruleset.get('name', 'ruleset').replace(' ', '_').lower()}.tsv"

    return output.getvalue(), filename
