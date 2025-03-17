import firebase_functions as functions
from flask import jsonify, render_template_string, request
from ..auth.token_verification import verify_firebase_token
from ..utils.speckle_api import get_user_projects, get_project_details
from ..templates.project_templates import (
    get_project_selection_template,
    get_project_details_template
)
from ..utils.firestore_utils import get_rulesets_for_project

@verify_firebase_token
async def get_user_projects_view():
    """Return HTML for the user's Speckle projects."""
    try:
        # Get user info from the request (added by verify_firebase_token decorator)
        user_id = request.user_id
        
        # Get speckle token from firestore
        speckle_token = await get_speckle_token_for_user(user_id)
        if not speckle_token:
            return render_template_string(
                '<div class="p-4 bg-red-100 text-red-700 rounded">Unable to access your Speckle token. Please sign out and sign in again.</div>'
            )
        
        # Fetch projects from Speckle API
        projects = await get_user_projects(speckle_token)
        
        # Return the rendered template
        return render_template_string(
            get_project_selection_template(),
            projects=projects
        )
    except Exception as e:
        return render_template_string(
            '<div class="p-4 bg-red-100 text-red-700 rounded">Error loading projects: {}</div>'.format(str(e))
        )

@verify_firebase_token
async def get_project_with_rulesets(project_id):
    """Return HTML for a project with its rulesets."""
    try:
        # Get user info from the request
        user_id = request.user_id
        
        # Get speckle token
        speckle_token = await get_speckle_token_for_user(user_id)
        if not speckle_token:
            return render_template_string(
                '<div class="p-4 bg-red-100 text-red-700 rounded">Unable to access your Speckle token. Please sign out and sign in again.</div>'
            )
        
        # Fetch project details from Speckle API
        project = await get_project_details(speckle_token, project_id)
        
        # Fetch rulesets for this project
        rulesets = await get_rulesets_for_project(user_id, project_id)
        
        # Return the rendered template
        return render_template_string(
            get_project_details_template(),
            project=project,
            rulesets=rulesets
        )
    except Exception as e:
        return render_template_string(
            '<div class="p-4 bg-red-100 text-red-700 rounded">Error loading project: {}</div>'.format(str(e))
        )

async def get_speckle_token_for_user(user_id):
    """Get the Speckle token for a user from Firestore."""
    from firebase_admin import firestore
    db = firestore.client()
    
    try:
        user_token_doc = await db.collection('userTokens').document(user_id).get()
        if user_token_doc.exists:
            return user_token_doc.to_dict().get('speckleToken')
        return None
    except Exception:
        return None

# Register routes
def register_routes(app):
    app.add_url_rule(
        '/api/projects',
        'get_user_projects_view',
        get_user_projects_view,
        methods=['GET']
    )
    app.add_url_rule(
        '/api/projects/<project_id>',
        'get_project_with_rulesets',
        get_project_with_rulesets,
        methods=['GET']
    )