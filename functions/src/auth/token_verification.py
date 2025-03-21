from functools import wraps
from firebase_admin import auth
import json
from firebase_functions import https_fn

def verify_firebase_token(func):
    """
    Decorator to verify Firebase ID token in the request.
    Adds user_id and user_email to the request object.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):

        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return https_fn.Response(
                json.dumps({"error": "Unauthorized - Missing or invalid token"}),
                mimetype="application/json",
                status=401
            )
        
        token = auth_header.split('Bearer ')[1]
        
        try:
            decoded_token = auth.verify_id_token(token)
            request.user_id = decoded_token['uid']
            request.user_email = decoded_token.get('email')
            return func(request, *args, **kwargs)
        
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
