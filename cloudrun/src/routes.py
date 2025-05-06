# cloudrun/src/routes.py - All Flask Routes with Session Management
from flask import (
    request,
    send_file,
    jsonify,
    render_template,
    session,
    redirect,
    url_for,
)
from .auth import (
    init_auth,
    exchange_token,
    verify_session,
    verify_token,
    get_user_token,
)
from .speckle import get_user_projects, get_project_details
from .database import (
    get_rulesets_for_project,
    get_rules_for_ruleset,
    create_ruleset,
    update_ruleset,
    delete_ruleset,
    toggle_ruleset_sharing,
)
from .mapping import generate_ruleset_tsv
from functools import wraps
import io
from google.cloud import firestore
import uuid


def setup_routes(app):
    """Setup all application routes"""

    # Authentication decorator for routes
    def require_auth(f):
        """Decorator to require authentication - checks session first"""

        @wraps(f)
        def decorated_function(*args, **kwargs):
            # First check session
            user_id = verify_session(app)

            if not user_id:
                # Check authorization header as fallback
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    user_id = verify_token(app, auth_header.split("Bearer ")[1])

            if not user_id:
                # Handle HTMX requests differently
                if request.headers.get("HX-Request"):
                    return render_template("error.html", message="Please log in"), 401
                return redirect(url_for("index"))

            # Store user_id in request context for handlers
            request.user_id = user_id
            return f(*args, **kwargs)

        return decorated_function

    # Static files
    @app.route("/")
    def index():
        return send_file("public/index.html")

    @app.route("/fbconfig.js")
    def fbconfig():
        return send_file("public/fbconfig.js")

    @app.route("/speckle-theme.css")
    def speckle_theme():
        return send_file("public/speckle-theme.css")

    @app.route("/htmx-styles.css")
    def htmx_styles():
        return send_file("public/htmx-styles.css")

    @app.route("/js/<path:filename>")
    def js_files(filename):
        return send_file(f"public/js/{filename}")

    @app.route("/img/<path:filename>")
    def img_files(filename):
        return send_file(f"public/img/{filename}")

    # Auth routes
    @app.route("/api/auth/init", methods=["GET"])
    def init_speckle_auth():
        return init_auth(app)

    @app.route("/api/auth/token", methods=["GET", "POST"])
    def token_exchange():
        return exchange_token(app, request)

    @app.route("/api/auth/signout", methods=["POST"])
    def sign_out():
        session.clear()
        return jsonify({"status": "signed out"}), 200

    @app.route("/api/auth/users", methods=["POST"])
    def auth_users():
        """Handle user info from Speckle auth flow"""
        token = request.json.get("token")
        refresh_token = request.json.get("refreshToken")

        if not token:
            return jsonify({"error": "Missing token"}), 400

        try:
            # Use Firebase Auth Admin SDK to create a custom token
            from firebase_admin import auth as firebase_auth

            # First, get user info from Speckle
            import requests

            profile_response = requests.post(
                f"{app.env['SPECKLE_SERVER_URL']}/graphql",
                headers={"Authorization": f"Bearer {token}"},
                json={"query": "query { activeUser { id name email avatar } }"},
            )

            if profile_response.status_code != 200:
                return jsonify({"error": "Failed to get user profile"}), 500

            user_data = profile_response.json()["data"]["activeUser"]

            # Create/update Firebase user
            try:
                firebase_user = firebase_auth.get_user_by_email(user_data["email"])
                # Update if needed
                if (
                    firebase_user.display_name != user_data["name"]
                    or firebase_user.photo_url != user_data["avatar"]
                ):
                    firebase_auth.update_user(
                        firebase_user.uid,
                        display_name=user_data["name"],
                        photo_url=user_data["avatar"],
                    )
            except firebase_auth.UserNotFoundError:
                import os

                firebase_user = firebase_auth.create_user(
                    email=user_data["email"],
                    display_name=user_data["name"],
                    photo_url=user_data["avatar"],
                    password=os.urandom(20).hex(),
                )

            # Store token in Firestore
            app.db.collection("userTokens").document(firebase_user.uid).set(
                {
                    "speckleId": user_data["id"],
                    "speckleToken": token,
                    "speckleRefreshToken": refresh_token,
                    "updatedAt": firestore.SERVER_TIMESTAMP,
                }
            )

            # Create custom token
            custom_token = firebase_auth.create_custom_token(firebase_user.uid)

            return jsonify(
                {
                    "customToken": (
                        custom_token.decode()
                        if hasattr(custom_token, "decode")
                        else custom_token
                    )
                }
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    # Project routes
    @app.route("/api/projects", methods=["GET"])
    @require_auth
    def get_projects():
        projects = get_user_projects(app, request.user_id)
        return render_template("project_selection.html", projects=projects)

    @app.route("/api/projects/<project_id>", methods=["GET"])
    @require_auth
    def get_project_view(project_id):
        rulesets = get_rulesets_for_project(app, request.user_id, project_id)
        project = get_project_details(app, request.user_id, project_id)

        # For each ruleset, add the rules count
        for ruleset in rulesets:
            rules = get_rules_for_ruleset(app, ruleset["id"])
            ruleset["rules"] = rules

        return render_template(
            "project_details.html", project=project, rulesets=rulesets
        )

    # Ruleset routes
    @app.route("/api/rulesets/new", methods=["GET"])
    @require_auth
    def new_ruleset_form():
        """Get the form for creating a new ruleset"""
        project_id = request.args.get("projectId")

        # Get project details for name
        project_name = "Project"  # Default
        project = get_project_details(app, request.user_id, project_id)
        if project:
            project_name = project.get("name", "Project")

        return render_template(
            "new_ruleset_form.html", project_id=project_id, project_name=project_name
        )

    @app.route("/api/rulesets", methods=["POST"])
    @require_auth
    def create_new_ruleset():
        project_id = request.form.get("projectId")
        name = request.form.get("name")
        description = request.form.get("description", "")

        ruleset = create_ruleset(app, request.user_id, project_id, name, description)

        # Redirect to edit page
        return redirect(url_for("edit_ruleset", ruleset_id=ruleset["id"]), code=303)

    @app.route("/api/rulesets/<ruleset_id>", methods=["GET"])
    @require_auth
    def edit_ruleset(ruleset_id):
        ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
        if not ruleset_doc.exists:
            return render_template("error.html", message="Ruleset not found"), 404

        ruleset = ruleset_doc.to_dict()
        ruleset["id"] = ruleset_id

        rules = get_rules_for_ruleset(app, ruleset_id)

        return render_template("edit_ruleset.html", ruleset=ruleset, rules=rules)

    @app.route("/api/rulesets/<ruleset_id>/delete", methods=["DELETE"])
    @require_auth
    def delete_ruleset_route(ruleset_id):
        delete_ruleset(app, ruleset_id)
        return "", 204

    @app.route("/api/rulesets/<ruleset_id>/share", methods=["PATCH"])
    @require_auth
    def toggle_share_ruleset(ruleset_id):
        is_shared = toggle_ruleset_sharing(app, ruleset_id)

        # Re-fetch ruleset data to render the updated card
        ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
        ruleset = ruleset_doc.to_dict()
        ruleset["id"] = ruleset_id
        ruleset["isShared"] = is_shared

        # Add rules for template
        rules = get_rules_for_ruleset(app, ruleset_id)
        ruleset["rules"] = rules

        return render_template("ruleset_card.html", ruleset=ruleset)

    @app.route("/api/rulesets/<ruleset_id>/export", methods=["GET"])
    @require_auth
    def export_ruleset(ruleset_id):
        # Get ruleset
        ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
        if not ruleset_doc.exists:
            return render_template("error.html", message="Ruleset not found"), 404

        ruleset = ruleset_doc.to_dict()
        rules = get_rules_for_ruleset(app, ruleset_id)

        # Generate TSV
        tsv_content, filename = generate_ruleset_tsv(ruleset, rules)

        # Return TSV file
        output = io.BytesIO()
        output.write(tsv_content.encode("utf-8"))
        output.seek(0)

        return send_file(
            output,
            mimetype="text/tab-separated-values",
            as_attachment=True,
            download_name=filename,  # Use download_name instead of attachment_filename
        )

    # Rule routes
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
        rules = get_rules_for_ruleset(app, ruleset_id)

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
        rules = get_rules_for_ruleset(app, ruleset_id)

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
        rules = get_rules_for_ruleset(app, ruleset_id)

        return render_template("rules_list.html", rules=rules, ruleset_id=ruleset_id)

    # Shared ruleset route (public)
    @app.route("/api/shared-rule-sets/<ruleset_id>", methods=["GET"])
    def get_shared_ruleset_api(ruleset_id):
        """API route for fetching shared ruleset"""
        ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
        if not ruleset_doc.exists:
            return render_template("error.html", message="Ruleset not found"), 404

        ruleset = ruleset_doc.to_dict()
        ruleset["id"] = ruleset_id

        if not ruleset.get("isShared", False):
            return (
                render_template("error.html", message="This ruleset is not shared"),
                403,
            )

        rules = get_rules_for_ruleset(app, ruleset_id)

        return render_template(
            "edit_ruleset.html", ruleset=ruleset, rules=rules, readonly=True
        )

    @app.route("/shared/<ruleset_id>")
    def shared_ruleset(ruleset_id):
        """Public page for shared rulesets"""
        ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
        if not ruleset_doc.exists:
            return render_template("error.html", message="Ruleset not found"), 404

        ruleset = ruleset_doc.to_dict()
        ruleset["id"] = ruleset_id

        if not ruleset.get("isShared", False):
            return (
                render_template("error.html", message="This ruleset is not shared"),
                403,
            )

        rules = get_rules_for_ruleset(app, ruleset_id)

        # For shared rulesets, we render directly to the client
        from flask import render_template_string

        with open("public/index.html", "r") as f:
            template = f.read()

        content = render_template(
            "edit_ruleset.html", ruleset=ruleset, rules=rules, readonly=True
        )
        html = template.replace(
            '<div id="main-content">', f'<div id="main-content">{content}'
        )

        return html
