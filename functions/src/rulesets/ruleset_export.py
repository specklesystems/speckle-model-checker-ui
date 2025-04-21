from firebase_functions import https_fn

from ..utils.firestore_utils import (
    get_ruleset,
    get_rules_for_ruleset,
    safe_verify_id_token,
)
from ..utils.tsv_utils import generate_ruleset_tsv


def export_ruleset_as_tsv(request, ruleset_id):
    """Export a ruleset as a TSV file."""
    try:
        # Get user info from request (if available)
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                id_token = auth_header.split("Bearer ")[1]
                decoded_token = safe_verify_id_token(id_token)
                user_id = decoded_token.get("uid")
            else:
                user_id = None
        except Exception:
            user_id = None

        # Get the ruleset
        ruleset = get_ruleset(ruleset_id)

        # If not found as a private ruleset, try as a shared ruleset
        if not ruleset:
            # For this function, we likely want to check if the ruleset is shared first
            print(f"Private ruleset {ruleset_id} not found, checking if shared...")
            return https_fn.Response(
                "Ruleset not found", mimetype="text/plain", status=404
            )

        # Verify ownership if not a shared ruleset
        if (
            not ruleset.get("isShared", False)
            and user_id
            and ruleset.get("userId") != user_id
        ):
            return https_fn.Response(
                "You don't have permission to export this ruleset",
                mimetype="text/plain",
                status=403,
            )

        # Get rules
        rules = get_rules_for_ruleset(ruleset_id)

        # Generate TSV content using the shared utility
        tsv_content, filename = generate_ruleset_tsv(ruleset, rules)

        # Set headers for file download
        return https_fn.Response(
            tsv_content,
            mimetype="text/tab-separated-values",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error details: {error_details}")
        return https_fn.Response(
            f"Error exporting ruleset: {str(e)}",
            mimetype="text/plain",
            status=500,
        )


# Create Firebase Function
def export_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")  # Extract from query params
    return export_ruleset_as_tsv(request, ruleset_id)
