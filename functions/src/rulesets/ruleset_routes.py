from firebase_functions import https_fn
from firebase_admin import firestore
import json
from ..auth.token_verification import verify_firebase_token
from ..utils.jinja_env import render_template
from ..utils.firestore_utils import (
    get_ruleset, 
    create_ruleset, 
    update_ruleset, 
    delete_ruleset
)
from ..utils.speckle_api import get_project_details

# Get Speckle token for a user from Firestore
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
async def get_ruleset_edit_form(request, ruleset_id):
    """Return HTML for editing a ruleset."""
    try:
        # Get user info from request
        user_id = request.user_id
        
        # Get the ruleset
        ruleset = await get_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="Ruleset not found"),
                mimetype="text/html",
                status=404
            )
        
        # Verify ownership
        if ruleset.get('userId') != user_id:
            return https_fn.Response(
                render_template('error.html', message="You don't have permission to edit this ruleset"),
                mimetype="text/html",
                status=403
            )
        
        # Return the form
        return https_fn.Response(
            render_template('edit_ruleset.html', ruleset=ruleset),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading ruleset: {str(e)}"),
            mimetype="text/html",
            status=500
        )

@verify_firebase_token
async def create_new_ruleset(request):
    """Create a new ruleset."""
    try:
        # Get form data
        form_data = await request.form
        project_id = form_data.get('projectId')
        name = form_data.get('name')
        description = form_data.get('description', '')
        
        if not project_id or not name:
            return https_fn.Response(
                render_template('error.html', message="Missing required fields"),
                mimetype="text/html",
                status=400
            )
        
        # Get user info from request
        user_id = request.user_id
        
        # Create the ruleset
        ruleset = await create_ruleset(user_id, project_id, name, description)
        
        # Redirect to the project page
        return https_fn.Response(
            f"""
            <div hx-get="/api/projects/{project_id}" hx-trigger="load" hx-target="#main-content">
                <div class="flex justify-center">
                    <svg class="animate-spin h-8 w-8 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                    </svg>
                </div>
            </div>
            """,
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error creating ruleset: {str(e)}"),
            mimetype="text/html",
            status=500
        )

@verify_firebase_token
async def update_ruleset_info(request, ruleset_id):
    """Update a ruleset's basic information."""
    try:
        # Get form data
        form_data = await request.form
        name = form_data.get('name')
        description = form_data.get('description', '')
        
        if not name:
            return https_fn.Response(
                render_template('error.html', message="Missing required fields"),
                mimetype="text/html",
                status=400
            )
        
        # Get user info from request
        user_id = request.user_id
        
        # Get current ruleset to verify ownership
        ruleset = await get_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="Ruleset not found"),
                mimetype="text/html",
                status=404
            )
        
        # Verify ownership
        if ruleset.get('userId') != user_id:
            return https_fn.Response(
                render_template('error.html', message="You don't have permission to edit this ruleset"),
                mimetype="text/html",
                status=403
            )
        
        # Update the ruleset
        await update_ruleset(ruleset_id, {
            'name': name,
            'description': description
        })
        
        # Reload the edit page
        return await get_ruleset_edit_form(request, ruleset_id)
    
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error updating ruleset: {str(e)}"),
            mimetype="text/html",
            status=500
        )


@verify_firebase_token
async def delete_ruleset_handler(request, ruleset_id):
    """Delete a ruleset."""
    try:
        # Get user info from request
        user_id = request.user_id
        
        # Get current ruleset to verify ownership and get project ID
        ruleset = await get_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="Ruleset not found"),
                mimetype="text/html",
                status=404
            )
        
        # Verify ownership
        if ruleset.get('userId') != user_id:
            return https_fn.Response(
                render_template('error.html', message="You don't have permission to delete this ruleset"),
                mimetype="text/html",
                status=403
            )
        
        # Save project ID before deletion
        project_id = ruleset.get('projectId')
        
        # Delete the ruleset
        await delete_ruleset(ruleset_id)
        
        # Return empty response (the element will be removed by htmx)
        return https_fn.Response("", mimetype="text/html")
    
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error deleting ruleset: {str(e)}"),
            mimetype="text/html",
            status=500
        )
# Create Firebase Functions
def get_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")  # Extract from query params
    return get_ruleset_edit_form(request, ruleset_id)

def update_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")
    return update_ruleset_info(request, ruleset_id)

def delete_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")  # Extract from query params
    return delete_ruleset(request, ruleset_id)

# Register Firebase functions
get_ruleset_fn = https_fn.on_request()(get_ruleset_handler)
create_ruleset_fn = https_fn.on_request()(create_new_ruleset)  # No need to change this
update_ruleset_fn = https_fn.on_request()(update_ruleset_handler)
delete_ruleset_fn = https_fn.on_request()(delete_ruleset_handler)
