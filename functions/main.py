import firebase_functions as functions
import firebase_admin
from firebase_admin import firestore
from flask import Flask, request, jsonify, render_template_string

# Initialize Firebase
firebase_admin.initialize_app()

# Create Flask app
app = Flask(__name__)

# Import route modules
from .auth import auth_routes
from .projects import project_routes
from .rulesets import ruleset_routes, ruleset_sharing, ruleset_export
from .rules import rule_routes

# Register routes
auth_routes.register_routes(app)
project_routes.register_routes(app)
ruleset_routes.register_routes(app)
ruleset_sharing.register_routes(app)
ruleset_export.register_routes(app)
rule_routes.register_routes(app)

# Error handling
@app.errorhandler(404)
def not_found(error):
    return render_template_string(
        '<div class="p-4 bg-red-100 text-red-700 rounded">Resource not found</div>'
    ), 404

@app.errorhandler(500)
def server_error(error):
    return render_template_string(
        '<div class="p-4 bg-red-100 text-red-700 rounded">Server error: {}</div>'.format(str(error))
    ), 500

# Create the cloud function
model_checker_api = functions.https_fn.on_request(app)