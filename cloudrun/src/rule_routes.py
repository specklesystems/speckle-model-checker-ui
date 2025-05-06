# cloudrun/src/rule_routes.py - Rule-specific endpoints
from flask import request, render_template, jsonify
from google.cloud import firestore
import uuid


def setup_rule_routes(app, require_auth):
    """Setup rule-related routes"""

    def get_rules_for_ruleset(ruleset_id):
        """Get all rules for a ruleset"""
        rules_ref = (
            app.db.collection("ruleSets")
            .document(ruleset_id)
            .collection("rules")
            .order_by("order")
        )
        rules_docs = rules_ref.get()

        rules = []
        for doc in rules_docs:
            rule = doc.to_dict()
            rule["id"] = doc.id
            rules.append(rule)

        return rules

    @app.route("/api/rulesets/<ruleset_id>/rules/new", methods=["GET"])
    @require_auth
    def new_rule_form(ruleset_id):
        """Get form for creating a new rule"""
        return render_template("new_rule_form.html", ruleset_id=ruleset_id)

    @app.route("/api/rule/condition", methods=["GET"])
    @require_auth
    def get_condition_row():
        """Get a new condition row for rule forms"""
        index = request.args.get("index", 1)
        ruleset_id = request.args.get("ruleset_id", "")
        return render_template("condition_row.html", index=index, ruleset_id=ruleset_id)

    @app.route("/api/rulesets/<ruleset_id>/rules", methods=["POST"])
    @require_auth
    def create_rule(ruleset_id):
        """Create a new rule for a ruleset"""
        # Get form data
        message = request.form.get("message")
        severity = request.form.get("severity", "Error")

        # Process conditions (multi-value form)
        conditions = []
        for i in range(100):  # arbitrary upper limit
            logic = request.form.get(f"conditions[{i}][logic]")
            if not logic:
                break

            property_name = request.form.get(f"conditions[{i}][propertyName]")
            predicate = request.form.get(f"conditions[{i}][predicate]")
            value = request.form.get(f"conditions[{i}][value]")

            if property_name and predicate:
                conditions.append(
                    {
                        "logic": logic,
                        "propertyName": property_name,
                        "predicate": predicate,
                        "value": value or "",
                    }
                )

        # Create rule document
        # Get current max order for this ruleset
        rules_ref = (
            app.db.collection("ruleSets").document(ruleset_id).collection("rules")
        )

        # Count existing rules to determine order
        existing_rules = list(rules_ref.stream())
        next_order = len(existing_rules) + 1

        rule_data = {
            "message": message,
            "severity": severity,
            "conditions": conditions,
            "order": next_order,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }

        # Generate rule ID
        rule_id = str(uuid.uuid4())

        # Add rule to ruleset
        rules_ref.document(rule_id).set(rule_data)

        # Update ruleset's updatedAt timestamp
        app.db.collection("ruleSets").document(ruleset_id).update(
            {"updatedAt": firestore.SERVER_TIMESTAMP}
        )

        # Get all rules to render the template
        rules = get_rules_for_ruleset(ruleset_id)

        return render_template("rules_list.html", rules=rules, ruleset_id=ruleset_id)

    @app.route("/api/rulesets/<ruleset_id>/rules/<rule_id>/edit", methods=["GET"])
    @require_auth
    def edit_rule_form(ruleset_id, rule_id):
        """Get form for editing a rule"""
        rule_doc = (
            app.db.collection("ruleSets")
            .document(ruleset_id)
            .collection("rules")
            .document(rule_id)
            .get()
        )

        if not rule_doc.exists:
            return render_template("error.html", message="Rule not found"), 404

        rule = rule_doc.to_dict()
        rule["id"] = rule_id

        return render_template("edit_rule_form.html", ruleset_id=ruleset_id, rule=rule)

    @app.route("/api/rulesets/<ruleset_id>/rules/<rule_id>", methods=["PUT"])
    @require_auth
    def update_rule(ruleset_id, rule_id):
        """Update an existing rule"""
        # Get form data
        message = request.form.get("message")
        severity = request.form.get("severity", "Error")

        # Process conditions (multi-value form)
        conditions = []
        for i in range(100):  # arbitrary upper limit
            logic = request.form.get(f"conditions[{i}][logic]")
            if not logic:
                break

            property_name = request.form.get(f"conditions[{i}][propertyName]")
            predicate = request.form.get(f"conditions[{i}][predicate]")
            value = request.form.get(f"conditions[{i}][value]")

            if property_name and predicate:
                conditions.append(
                    {
                        "logic": logic,
                        "propertyName": property_name,
                        "predicate": predicate,
                        "value": value or "",
                    }
                )

        # Update rule document
        rule_data = {
            "message": message,
            "severity": severity,
            "conditions": conditions,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }

        # Update rule
        app.db.collection("ruleSets").document(ruleset_id).collection("rules").document(
            rule_id
        ).update(rule_data)

        # Update ruleset's updatedAt timestamp
        app.db.collection("ruleSets").document(ruleset_id).update(
            {"updatedAt": firestore.SERVER_TIMESTAMP}
        )

        # Get all rules to render the template
        rules = get_rules_for_ruleset(ruleset_id)

        return render_template("rules_list.html", rules=rules, ruleset_id=ruleset_id)

    @app.route("/api/rulesets/<ruleset_id>/rules/<rule_id>", methods=["DELETE"])
    @require_auth
    def delete_rule(ruleset_id, rule_id):
        """Delete a rule"""
        # Delete rule document
        app.db.collection("ruleSets").document(ruleset_id).collection("rules").document(
            rule_id
        ).delete()

        # Update ruleset's updatedAt timestamp
        app.db.collection("ruleSets").document(ruleset_id).update(
            {"updatedAt": firestore.SERVER_TIMESTAMP}
        )

        # Get all rules to render the template
        rules = get_rules_for_ruleset(ruleset_id)

        return render_template("rules_list.html", rules=rules, ruleset_id=ruleset_id)
