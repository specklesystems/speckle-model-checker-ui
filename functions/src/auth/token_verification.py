from firebase_functions import https_fn
from firebase_admin import auth
import json
from functools import wraps

def verify_firebase_token(func):
    """
    Decorator to verify Firebase ID token in the request.
    Adds user_id and user_email to the request object.
    """
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return https_fn.Response(
                json.dumps({"error": "Unauthorized - Missing or invalid token"}),
                mimetype="application/json",
                status=401
            )
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            
            # Add user info to the request
            request.user_id = decoded_token['uid']
            request.user_email = decoded_token.get('email')
            
            # Continue to the handler function
            return await func(request, *args, **kwargs)
        
        except auth.InvalidIdTokenError:
            return https_fn.Response(
                json.dumps({"error": "Unauthorized - Invalid token"}),
                mimetype="application/json",
                status=401
            )
        except auth.ExpiredIdTokenError:
            return https_fn.Response(
                json.dumps({"error": "Unauthorized - Token expired"}),
                mimetype="application/json",
                status=401
            )
        except Exception as e:
            return https_fn.Response(
                json.dumps({"error": f"Unauthorized - {str(e)}"}),
                mimetype="application/json",
                status=401
            )
    
    return wrapper