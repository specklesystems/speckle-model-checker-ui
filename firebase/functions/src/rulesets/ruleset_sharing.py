from firebase_functions import https_fn
import csv
from io import StringIO

from ..projects.project_routes import get_location
from ..utils.firestore_utils import (
    get_rules_for_ruleset,
    get_ruleset,
    safe_verify_id_token,
    toggle_ruleset_sharing,
)
from ..utils.jinja_env import render_template
from ..utils.tsv_utils import generate_ruleset_tsv


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

        # Try using the shared utility first
        try:
            # Generate TSV content using the shared utility
            tsv_content, filename = generate_ruleset_tsv(ruleset, rules)
        except Exception as util_error:
            print(
                f"Shared utility error: {util_error}. Falling back to inline generation."
            )
            # Fall back to inline generation if the utility fails
            tsv_content, filename = _generate_tsv_inline(ruleset, rules)

        # Return TSV file directly - this is important for automation
        return https_fn.Response(
            tsv_content,
            mimetype="text/tab-separated-values",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/tab-separated-values",
            },
        )
    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error in get_shared_ruleset_view: {str(e)}")
        print(f"Error details: {error_details}")
        return https_fn.Response(
            f"Error serving shared ruleset: {str(e)}",
            mimetype="text/plain",
            status=500,
        )


def _generate_tsv_inline(ruleset, rules):
    """
    Inline TSV generation as a fallback.
    Puts severity and message on the last row of each rule.
    """
    # Generate TSV
    output = StringIO()
    writer = csv.writer(output, delimiter="\t")

    # Write header with "Rule Number" instead of "Rule #"
    writer.writerow(
        [
            "Rule Number",
            "Logic",
            "Property Name",
            "Predicate",
            "Value",
            "Report Severity",
            "Message",
        ]
    )

    # Write rules
    rule_number = 1
    for rule in rules:
        # Get all conditions for this rule
        conditions = rule.get("conditions", [])

        # Skip empty rules
        if not conditions:
            continue

        # For each condition except the last one
        for i, condition in enumerate(conditions[:-1]):
            row = []

            # Only include rule number on first row
            if i == 0:
                row.append(str(rule_number))  # Rule number
            else:
                row.append("")  # Empty rule number for middle conditions

            row.append(condition.get("logic", ""))  # Logic
            row.append(condition.get("propertyName", ""))  # Property Path
            row.append(condition.get("predicate", ""))  # Predicate
            row.append(condition.get("value", ""))  # Value
            row.append("")  # Empty severity for non-last conditions
            row.append("")  # Empty message for non-last conditions

            writer.writerow(row)

        # For the last condition, include severity and message
        if conditions:
            last_condition = conditions[-1]
            row = []

            # Only include rule number on first row if there was only one condition
            if len(conditions) == 1:
                row.append(str(rule_number))  # Rule number
            else:
                row.append(
                    ""
                )  # Empty rule number for last condition if not the only condition

            row.append(last_condition.get("logic", ""))  # Logic
            row.append(last_condition.get("propertyName", ""))  # Property Path
            row.append(last_condition.get("predicate", ""))  # Predicate
            row.append(last_condition.get("value", ""))  # Value
            row.append(rule.get("severity", "Error"))  # Severity on last row
            row.append(rule.get("message", ""))  # Message on last row

            writer.writerow(row)

        rule_number += 1

    # Create filename based on ruleset name
    filename = f"{ruleset.get('name', 'ruleset').replace(' ', '_').lower()}.tsv"

    return output.getvalue(), filename
