import re

from firebase_functions import https_fn
from google.cloud import firestore

from ..utils.firestore_utils import (
    create_rule,
    delete_single_rule,
    get_rule,
    get_rules_for_ruleset,
    get_ruleset,
    safe_verify_id_token,
    update_single_rule,
)
from ..utils.jinja_env import render_template
from ..utils.mapping import get_canonical_predicate


def get_rules(request, ruleset_id):
    """Return HTML for all rules in a ruleset."""
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
                    message="You don't have permission to view these rules",
                ),
                mimetype="text/html",
                status=403,
            )

        # Get rules from the subcollection
        rules = get_rules_for_ruleset(ruleset_id)

        # Convert any symbolic storage predicates to canonical forms for display
        for rule in rules:
            for condition in rule.get("conditions", []):
                if "predicate" in condition:
                    stored_predicate = condition["predicate"]
                    canonical_predicate = get_canonical_predicate(stored_predicate)
                    condition["predicate"] = canonical_predicate

        # Return the rules list
        return https_fn.Response(
            render_template(
                "rules_list.html",
                ruleset=ruleset,
                ruleset_id=ruleset_id,
                rules=rules,
            ),
            mimetype="text/html",
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error loading rules: {str(e)}")
        print(f"Error details: {error_details}")
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


def get_edit_rule_form(request, ruleset_id, rule_id):
    """Return HTML for editing a rule."""
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

        # Get the rule from the rules subcollection
        rule = get_rule(ruleset_id, rule_id)

        if not rule:
            return https_fn.Response(
                render_template("error.html", message="Rule not found"),
                mimetype="text/html",
                status=404,
            )

        # Debug: Log the original rule data including predicates
        print(f"Original rule data: {rule}")
        print(f"Rule conditions before normalization:")
        for i, condition in enumerate(rule.get("conditions", [])):
            print(f"  Condition {i}: predicate = '{condition.get('predicate')}'")

        # Convert any symbolic storage predicates to canonical forms
        for condition in rule.get("conditions", []):
            if "predicate" in condition:
                stored_predicate = condition["predicate"]
                canonical_predicate = get_canonical_predicate(stored_predicate)
                condition["predicate"] = canonical_predicate

        # Debug: Log the normalized rule data for template
        print(f"Rule conditions after normalization:")
        for i, condition in enumerate(rule.get("conditions", [])):
            print(f"  Condition {i}: predicate = '{condition.get('predicate')}'")

        # Return the edit form
        return https_fn.Response(
            render_template(
                "edit_rule_form.html",
                ruleset_id=ruleset_id,
                rule_id=rule_id,
                rule=rule,
            ),
            mimetype="text/html",
        )

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error loading edit form: {str(e)}")
        print(f"Error details: {error_details}")
        return https_fn.Response(
            render_template("error.html", message=f"Error loading form: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def get_condition_row(index):
    """Return HTML for a new condition row."""
    try:
        index = int(index)

        # Return the condition row template
        return https_fn.Response(
            render_template("condition_row.html", index=index),
            mimetype="text/html",
        )

    except Exception as e:
        return https_fn.Response(
            render_template(
                "error.html",
                message=f"Error generating condition row: {str(e)}",
            ),
            mimetype="text/html",
            status=500,
        )


def create_rule_handler(request, ruleset_id):
    """Create a new rule for a ruleset."""
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

        # Get form data
        form_data = request.form
        message = form_data.get("message")
        severity = form_data.get("severity")

        # Log the form data for debugging
        print(f"Create rule form data: {dict(form_data)}")

        # Dynamically find all condition indexes
        condition_indexes = set()
        pattern = re.compile(r"conditions\[(\d+)\]\[logic\]")
        for key in form_data.keys():
            match = pattern.match(key)
            if match:
                condition_indexes.add(int(match.group(1)))

        conditions = []
        for i in sorted(condition_indexes):
            # Extract all condition fields including predicate
            logic = form_data.get(f"conditions[{i}][logic]")
            property_name = form_data.get(f"conditions[{i}][propertyName]")
            predicate = form_data.get(f"conditions[{i}][predicate]")
            value = form_data.get(f"conditions[{i}][value]")

            # Use predicate directly (already in canonical form)

            # Only add valid conditions
            if property_name and (predicate or logic == "CHECK"):
                conditions.append(
                    {
                        "logic": logic,
                        "propertyName": property_name,
                        "predicate": predicate,
                        "value": value,
                    }
                )

        # Log the processed conditions for debugging
        print(f"Processed conditions: {conditions}")

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

        # Enforce logic rules
        if conditions:
            conditions[0]["logic"] = "WHERE"
            for c in conditions[1:-1]:
                # Only force AND if it's not the CHECK condition
                if c["logic"] != "CHECK":
                    c["logic"] = "AND"

            # Don't change the last condition's logic if it's CHECK
            # but ensure all other conditions aren't CHECK
            for i in range(len(conditions) - 1):
                if conditions[i]["logic"] == "CHECK":
                    conditions[i]["logic"] = "AND"

        # Create rule data
        rule_data = {
            "message": message,
            "severity": severity,
            "conditions": conditions,
        }

        # Create rule in Firestore
        created_rule = create_rule(ruleset_id, user_id, rule_data)

        print(f"Created rule with data: {created_rule}")

        # Return updated rules list
        return get_rules(request, ruleset_id)

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error creating rule: {str(e)}")
        print(f"Error details: {error_details}")
        return https_fn.Response(
            render_template("error.html", message=f"Error creating rule: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def update_rule_handler(request, ruleset_id, rule_id):
    """Update an existing rule."""
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

        # Get form data
        form_data = request.form
        message = form_data.get("message")
        severity = form_data.get("severity")

        # Log the form data for debugging
        print(f"Update rule form data: {dict(form_data)}")

        # Dynamically find all condition indexes
        condition_indexes = set()
        pattern = re.compile(r"conditions\[(\d+)\]\[logic\]")
        for key in form_data.keys():
            match = pattern.match(key)
            if match:
                condition_indexes.add(int(match.group(1)))

        conditions = []
        for i in sorted(condition_indexes):
            # Extract the predicate value - it should already be in canonical form from the UI
            predicate = form_data.get(f"conditions[{i}][predicate]")

            # Store the predicate directly (canonical form)
            conditions.append(
                {
                    "logic": form_data.get(f"conditions[{i}][logic]"),
                    "propertyName": form_data.get(f"conditions[{i}][propertyName]"),
                    "predicate": predicate,
                    "value": form_data.get(f"conditions[{i}][value]"),
                }
            )

        # Log the processed conditions for debugging
        print(f"Processed conditions for update: {conditions}")

        # Enforce logic rules
        if conditions:
            conditions[0]["logic"] = "WHERE"
            for c in conditions[1:-1]:
                # Only force AND if it's not the CHECK condition
                if c["logic"] != "CHECK":
                    c["logic"] = "AND"

            # Don't change the last condition's logic if it's CHECK
            # but ensure all other conditions aren't CHECK
            for i in range(len(conditions) - 1):
                if conditions[i]["logic"] == "CHECK":
                    conditions[i]["logic"] = "AND"

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
                    message="You don't have permission to edit this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Verify rule exists
        rule = get_rule(ruleset_id, rule_id)
        if not rule:
            return https_fn.Response(
                render_template("error.html", message="Rule not found"),
                mimetype="text/html",
                status=404,
            )

        # Update rule data
        rule_data = {
            "message": message,
            "severity": severity,
            "conditions": conditions,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }

        # Update rule in Firestore
        update_single_rule(ruleset_id, rule_id, rule_data)

        # Return updated rules list
        return get_rules(request, ruleset_id)

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        print(f"Error updating rule: {str(e)}")
        print(f"Error details: {error_details}")
        return https_fn.Response(
            render_template("error.html", message=f"Error updating rule: {str(e)}"),
            mimetype="text/html",
            status=500,
        )


def delete_rule_handler(request, ruleset_id, rule_id):
    """Delete an existing rule."""
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
                    message="You don't have permission to delete rules from this ruleset",
                ),
                mimetype="text/html",
                status=403,
            )

        # Verify rule exists
        rule = get_rule(ruleset_id, rule_id)
        if not rule:
            return https_fn.Response(
                render_template("error.html", message="Rule not found"),
                mimetype="text/html",
                status=404,
            )

        # Delete rule from Firestore
        delete_single_rule(ruleset_id, rule_id)

        # Return updated rules list
        return get_rules(request, ruleset_id)

    except Exception as e:
        return https_fn.Response(
            render_template("error.html", message=f"Error deleting rule: {str(e)}"),
            mimetype="text/html",
            status=500,
        )
