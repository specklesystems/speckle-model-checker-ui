from firebase_functions import https_fn
from firebase_admin import firestore
import json
from ..auth.token_verification import verify_firebase_token
from ..utils.jinja_env import render_template
from ..utils.speckle_api import get_user_projects, get_project_details
from ..utils.firestore_utils import get_rulesets_for_project

# Function to get Speckle token for a user from Firestore
async def get_speckle_token_for_user(user_id):
    """Get the Speckle token for a user from Firestore."""
    db = firestore.client()
    
    try:
        user_token_doc = db.collection('userTokens').document(user_id).get()
        if user_token_doc.exists:
            return user_token_doc.to_dict().get('speckleToken')
        return None
    except Exception:
        return None

@verify_firebase_token
async def get_user_projects_view(request):
    """Return HTML for the user's Speckle projects."""
    try:
        # Get user info from the request (added by verify_firebase_token decorator)
        user_id = request.user_id
        
        # Get speckle token from firestore
        speckle_token = await get_speckle_token_for_user(user_id)
        if not speckle_token:
            return https_fn.Response(
                render_template('error.html', message="Unable to access your Speckle token. Please sign out and sign in again."),
                mimetype="text/html"
            )
        
        # Fetch projects from Speckle API
        projects = await get_user_projects(speckle_token)
        
        # Return the rendered template
        return https_fn.Response(
            render_template('project_selection.html', projects=projects),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading projects: {str(e)}"),
            mimetype="text/html"
        )

@verify_firebase_token
async def get_project_with_rulesets(request, project_id):
    """Return HTML for a project with its rulesets."""
    try:
        # Get user info from the request
        user_id = request.user_id
        
        # Get speckle token
        speckle_token = await get_speckle_token_for_user(user_id)
        if not speckle_token:
            return https_fn.Response(
                render_template('error.html', message="Unable to access your Speckle token. Please sign out and sign in again."),
                mimetype="text/html"
            )
        
        # Fetch project details from Speckle API
        project = await get_project_details(speckle_token, project_id)
        
        # Fetch rulesets for this project
        rulesets = await get_rulesets_for_project(user_id, project_id)
        
        # Get host URL for generating shared links
        host_url = request.headers.get('Host', '')
        if not host_url.startswith('http'):
            protocol = 'https' if not host_url.startswith('localhost') else 'http'
            location_origin = f"{protocol}://{host_url}"
        else:
            location_origin = host_url
        
        # Return the rendered template
        return https_fn.Response(
            render_template(
                'project_details.html',
                project=project,
                rulesets=rulesets,
                location_origin=location_origin
            ),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading project: {str(e)}"),
            mimetype="text/html"
        )

@verify_firebase_token
async def get_new_ruleset_form(request):
    """Return HTML for creating a new ruleset."""
    try:
        # Get project ID from query string
        project_id = request.args.get('projectId')
        if not project_id:
            return https_fn.Response(
                render_template('error.html', message="Missing project ID"),
                mimetype="text/html",
                status=400
            )
        
        # Get user info from request
        user_id = request.user_id
        
        # Get Speckle token
        speckle_token = await get_speckle_token_for_user(user_id)
        if not speckle_token:
            return https_fn.Response(
                render_template('error.html', message="Unable to access your Speckle token"),
                mimetype="text/html",
                status=401
            )
        
        # Get project details to show the name
        project = await get_project_details(speckle_token, project_id)
        if not project:
            return https_fn.Response(
                render_template('error.html', message="Project not found"),
                mimetype="text/html",
                status=404
            )
        
        # Return the form
        return https_fn.Response(
            render_template(
                'new_ruleset_form.html',
                project_id=project_id,
                project_name=project["name"]
            ),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading form: {str(e)}"),
            mimetype="text/html",
            status=500
        )

# Create Firebase Functions
get_projects_fn = https_fn.on_request()(get_user_projects_view)

def get_project_details(request, project_id):
    return get_project_with_rulesets(request, project_id)

get_project_details_fn = https_fn.on_request()(get_project_details)
get_new_ruleset_form_fn = https_fn.on_request()(get_new_ruleset_form)