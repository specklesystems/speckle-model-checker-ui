from firebase_functions import https_fn, options
import firebase_admin
from firebase_admin import firestore
import logging

from flask import Request

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Firebase (only if not already initialized)
if not firebase_admin._apps:
    firebase_admin.initialize_app()

# Import all function modules
from src.auth.auth_routes import init_speckle_auth, exchange_token
from src.projects.project_routes import (
    get_projects_fn, 
    get_project_details_fn, 
    get_new_ruleset_form_fn
)
from src.rulesets.ruleset_routes import (
    create_ruleset_fn, 
    get_ruleset_fn, 
    update_ruleset_fn, 
    delete_ruleset_fn
)
from src.rulesets.ruleset_sharing import (
    get_share_dialog_fn,
    toggle_sharing_fn,
    get_shared_ruleset_fn
)
from src.rulesets.ruleset_export import export_ruleset_fn
from src.rules.rule_routes import (
    get_rules_fn,
    get_new_rule_form_fn,
    get_edit_rule_form_fn,
    get_condition_row_fn
)


# Define CORS options (Modify as needed)
cors_config = options.CorsOptions(
    cors_origins=[r".*"],  # Allow all origins
    cors_methods=["get", "post"]
)


# Register Firebase Functions with CORS and proper decorator usage
@https_fn.on_request(cors=cors_config)
def init_auth_fn(req: https_fn.Request) -> https_fn.Response:
    return init_speckle_auth(req)

@https_fn.on_request(cors=cors_config)
def callback_handler(req: https_fn.Request) -> https_fn.Response:
    return exchange_token(req)