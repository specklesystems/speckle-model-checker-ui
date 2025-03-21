from firebase_functions import https_fn
from firebase_admin import auth
from google.cloud import firestore
from ..auth.token_verification import verify_firebase_token
from ..utils.jinja_env import render_template
from ..utils.firestore_utils import get_ruleset, update_ruleset, safe_verify_id_token


def get_rules(request, ruleset_id):
    """Return HTML for all rules in a ruleset."""
    try:
        # Get user info from request
        user_id = request.user_id

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
                    message="You don't have permission to view these rules",
                ),
                mimetype="text/html",
                status=403,
            )

        # Get rules from the ruleset
        rules = ruleset.get("rules", [])

        # Return the rules list
        return https_fn.Response(
            render_template("rules_list.html", ruleset_id=ruleset_id, rules=rules),
            mimetype="text/html",
        )

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading rules: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_new_rule_form(request, ruleset_id):
    """Return HTML for the new rule form."""
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

        # Get the ruleset to verify ownership
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
                    message="You don't have permission to add rules to this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Return the form
        return https_fn.Response(
            render_template("new_rule_form.html", ruleset_id=ruleset_id),
            mimetype="text/html",
        )

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading form: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_edit_rule_form(request, ruleset_id, rule_index):
    """Return HTML for editing a rule."""
    try:
        # Convert rule_index to int
        rule_index = int(rule_index)

        # Get user info from request
        user_id = request.user_id

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

        # Get the rule
        rules = ruleset.get("rules", [])

        if rule_index < 0 or rule_index >= len(rules):
            return https_fn.Response(
                render_template("error.html", message="Rule not found"),
                mimetype="text/html",
                status=404,
            )

        rule = rules[rule_index]

        # Return the edit form
        return https_fn.Response(
            render_template(
                "edit_rule_form.html",
                ruleset_id=ruleset_id,
                rule_index=rule_index,
                rule=rule,
            ),
            mimetype="text/html",
        )

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error loading form: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_condition_row(request, ruleset_id, index):
    """Return HTML for a new condition row."""
    try:
        # Convert index to int
        index = int(index)

        # Return the condition row template
        return https_fn.Response(
            render_template("condition_row.html", ruleset_id=ruleset_id, index=index),
            mimetype="text/html",
        )

    except Exception as e:
        return https_fn.Response(
            render_template(
                "error.html", message=f"Error generating condition row: {str(e)}"
            ),
            mimetype="text/html",
            status=500,
        )

