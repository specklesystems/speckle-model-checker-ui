from firebase_functions import https_fn, options
import firebase_admin
from firebase_admin import firestore, credentials
import json
import logging

from google.api_core.exceptions import GoogleAPICallError
from google.cloud import secretmanager


def load_firebase_cred_with_fallback():
    try:
        client = secretmanager.SecretManagerServiceClient()
        secret_name = "projects/speckle-model-checker/secrets/firebase-service-account-key/versions/latest"
        response = client.access_secret_version(name=secret_name)
        secret_payload = response.payload.data.decode("UTF-8")
        cred_info = json.loads(secret_payload)
        print("Loaded Firebase credentials from Secret Manager.")
        return credentials.Certificate(cred_info)
    except GoogleAPICallError as e:
        print(f"Could not load secret (probably emulator or no permission): {e}")
        print("Falling back to ADC / default credentials.")
        return None  # Will trigger default ADC fallback


# Initialize Firebase (only if not already initialized)
if not firebase_admin._apps:
    cred = load_firebase_cred_with_fallback()
    if cred:
        firebase_admin.initialize_app(cred)
    else:
        firebase_admin.initialize_app()  # Use ADC or environment creds

# Configure logging
logging.basicConfig(level=logging.INFO)

# Import all function modules
from src.auth.auth_routes import init_speckle_auth, exchange_token, get_user
from src.projects.project_routes import (
    get_user_projects_view,
    get_project_with_rulesets,
    get_new_ruleset_form,
)
from src.rulesets.ruleset_routes import (
    get_ruleset_edit_form,
    create_new_ruleset,
    update_ruleset_info,
    delete_ruleset_handler,
)
from src.rulesets.ruleset_sharing import (
    get_share_dialog,
    toggle_ruleset_sharing_handler,
    get_shared_ruleset_view,
)
from src.rulesets.ruleset_export import export_ruleset_as_tsv
from src.rules.rule_routes import (
    get_rules,
    get_new_rule_form,
    get_edit_rule_form,
    get_condition_row,
    update_rule_handler,
    create_rule_handler,
    delete_rule_handler,
)


# Define CORS options
cors_config = options.CorsOptions(
    cors_origins=[r".*"],  # Allow all origins
    cors_methods=["get", "post", "put", "delete"],
)


# Register Firebase Functions with CORS
@https_fn.on_request(cors=cors_config)
def init_auth_fn(req: https_fn.Request) -> https_fn.Response:
    return init_speckle_auth(req)


@https_fn.on_request(cors=cors_config)
def token_exchange_fn(req: https_fn.Request) -> https_fn.Response:
    return exchange_token(req)


@https_fn.on_request(cors=cors_config)
def get_users_fn(req: https_fn.Request) -> https_fn.Response:
    return get_user(req)


# Project Functions
@https_fn.on_request(cors=cors_config)
def get_projects_fn(req: https_fn.Request) -> https_fn.Response:
    return get_user_projects_view(req)


@https_fn.on_request(cors=cors_config)
def get_user_projects_fn(req: https_fn.Request) -> https_fn.Response:
    return get_user_projects_view(req)


@https_fn.on_request(cors=cors_config)
def get_project_details_fn(req: https_fn.Request) -> https_fn.Response:
    return get_project_with_rulesets(req)


@https_fn.on_request(cors=cors_config)
def get_new_ruleset_form_fn(req: https_fn.Request) -> https_fn.Response:
    return get_new_ruleset_form(req)


# Ruleset Functions
@https_fn.on_request(cors=cors_config)
def get_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id") or req.path.split("/rulesets/")[-1].split("/")[0]
    )
    return get_ruleset_edit_form(req, ruleset_id)


@https_fn.on_request(cors=cors_config)
def create_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    return create_new_ruleset(req)


@https_fn.on_request(cors=cors_config)
def update_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id") or req.path.split("/rulesets/")[-1].split("/")[0]
    )
    return update_ruleset_info(req, ruleset_id)


@https_fn.on_request(cors=cors_config)
def delete_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id") or req.path.split("/rulesets/")[-1].split("/")[0]
    )
    return delete_ruleset_handler(req, ruleset_id)


@https_fn.on_request(cors=cors_config)
def toggle_sharing_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id")
        or req.path.split("/share")[0].split("/")[-1]
    )

    return toggle_ruleset_sharing_handler(req, ruleset_id)


@https_fn.on_request(cors=cors_config)
def get_shared_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    
    parts = req.path.split("/")
    print(f"Request path: {req.path}")
    print(f"Parts: {parts}")
    
    ruleset_id = (
        req.args.get("ruleset_id")
        or req.path.split("/shared/")[-1].split("/")[0]
    )

    print(f"Ruleset ID: {ruleset_id}")
    return get_shared_ruleset_view(req, ruleset_id)


# Ruleset Export Function
@https_fn.on_request(cors=cors_config)
def export_ruleset_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id") or req.path.split("/export")[-2].split("/")[-1]
    )
    return export_ruleset_as_tsv(req, ruleset_id)


# Rule Functions
@https_fn.on_request(cors=cors_config)
def get_rules_fn(req: https_fn.Request) -> https_fn.Response:

    # Extract ruleset_id from path like /api/rulesets/{ruleset_id}/rules
    ruleset_id = (
        req.path.split("/rulesets/")[1].split("/")[0]
        if "/rulesets/" in req.path
        else req.args.get("ruleset_id")
    )
    # Route based on HTTP method
    if req.method == "GET":
        return get_rules(req, ruleset_id)
    elif req.method == "POST":

        return create_rule_handler(req, ruleset_id)
    else:
        return https_fn.Response(
            json.dumps({"error": f"Method {req.method} not allowed"}),
            mimetype="application/json",
            status=405,
        )


@https_fn.on_request(cors=cors_config)
def update_rule_fn(req: https_fn.Request) -> https_fn.Response:
    parts = req.path.split("/")
    ruleset_id = req.args.get("ruleset_id") or parts[-3]
    rule_index = req.args.get("rule_index") or parts[-1]

    # Route based on HTTP method
    if req.method == "DELETE":
        return delete_rule_handler(req, ruleset_id, rule_index)
    elif req.method == "PUT":
        return update_rule_handler(req, ruleset_id, rule_index)
    else:
        return https_fn.Response(
            json.dumps({"error": f"Method {req.method} not allowed"}),
            mimetype="application/json",
            status=405,
        )


@https_fn.on_request(cors=cors_config)
def get_new_rule_form_fn(req: https_fn.Request) -> https_fn.Response:
    ruleset_id = (
        req.args.get("ruleset_id") or req.path.split("/rules/new")[0].split("/")[-1]
    )
    return get_new_rule_form(req, ruleset_id)


@https_fn.on_request(cors=cors_config)
def get_condition_row_fn(req: https_fn.Request) -> https_fn.Response:

    index = req.args.get("index")

    if not index: 
        return https_fn.Response(
            json.dumps({"error": "Index not found"}),
            mimetype="application/json",
            status=400,
        )

    return get_condition_row(index)


@https_fn.on_request(cors=cors_config)
def get_edit_rule_form_fn(req: https_fn.Request) -> https_fn.Response:
    parts = req.path.split("/")

    print(f"Request path: {req.path}")

    if len(parts) < 5:
        return https_fn.Response(
            json.dumps({"error": "Invalid URL path"}),
            mimetype="application/json",
            status=400,
        )

    ruleset_id = req.args.get("ruleset_id") or parts[-4]
    rule_index = req.args.get("rule_index") or parts[-2]
    return get_edit_rule_form(req, ruleset_id, rule_index)
