from firebase_functions import https_fn
import json
from ..auth.token_verification import verify_firebase_token
from ..utils.jinja_env import render_template
from ..utils.firestore_utils import get_ruleset, toggle_ruleset_sharing, get_shared_ruleset

def get_share_dialog(request, ruleset_id):
    """Return HTML for the sharing dialog."""
    try:
        # Get user info from request
        user_id = request.user_id
        
        # Get the ruleset
        ruleset =  get_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="Ruleset not found"),
                mimetype="text/html",
                status=404
            )
        
        # Verify ownership
        if ruleset.get('userId') != user_id:
            return https_fn.Response(
                render_template('error.html', message="You don't have permission to share this ruleset"),
                mimetype="text/html",
                status=403
            )
        
        # Get host URL for generating shared links
        host_url = request.headers.get('Host', '')
        if not host_url.startswith('http'):
            protocol = 'https' if not host_url.startswith('localhost') else 'http'
            location_origin = f"{protocol}://{host_url}"
        else:
            location_origin = host_url
        
        # Return the dialog
        return https_fn.Response(
            render_template(
                'share_dialog.html',
                ruleset=ruleset,
                location_origin=location_origin
            ),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading sharing dialog: {str(e)}"),
            mimetype="text/html",
            status=500
        )

@verify_firebase_token
async def toggle_ruleset_sharing_handler(request, ruleset_id):
    """Toggle sharing status for a ruleset."""
    try:
        # Get user info from request
        user_id = request.user_id
        
        # Get the ruleset
        ruleset =  get_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="Ruleset not found"),
                mimetype="text/html",
                status=404
            )
        
        # Verify ownership
        if ruleset.get('userId') != user_id:
            return https_fn.Response(
                render_template('error.html', message="You don't have permission to share this ruleset"),
                mimetype="text/html",
                status=403
            )
        
        # Toggle sharing
        is_shared =  toggle_ruleset_sharing(ruleset_id)
        
        # Return the updated status
        return https_fn.Response(
            render_template('toggle_sharing.html', is_shared=is_shared),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error toggling sharing: {str(e)}"),
            mimetype="text/html",
            status=500
        )

async def get_shared_ruleset_view(request, ruleset_id):
    """Return HTML for a publicly shared ruleset."""
    try:
        # Get the shared ruleset (only returns if it's shared)
        ruleset =  get_shared_ruleset(ruleset_id)
        
        if not ruleset:
            return https_fn.Response(
                render_template('error.html', message="This ruleset is not available or not shared."),
                mimetype="text/html",
                status=404
            )
        
        # Return the ruleset view
        return https_fn.Response(
            render_template('shared_ruleset.html', ruleset=ruleset),
            mimetype="text/html"
        )
    except Exception as e:
        return https_fn.Response(
            render_template('error.html', message=f"Error loading shared ruleset: {str(e)}"),
            mimetype="text/html",
            status=500
        )

# Create Firebase Functions
def get_share_dialog_handler(request):
    ruleset_id = request.args.get("ruleset_id")  # Extract from query params
    return get_share_dialog(request, ruleset_id)

def toggle_sharing_handler(request):
    ruleset_id = request.args.get("ruleset_id")
    return toggle_ruleset_sharing_handler(request, ruleset_id)

def get_shared_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")
    return get_shared_ruleset_view(request, ruleset_id)

# Register Firebase functions
get_share_dialog_fn = https_fn.on_request()(get_share_dialog_handler)
toggle_sharing_fn = https_fn.on_request()(toggle_sharing_handler)
get_shared_ruleset_fn = https_fn.on_request()(get_shared_ruleset_handler)
