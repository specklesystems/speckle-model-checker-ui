import base64
import hashlib
import json
import os
import secrets
import string
from datetime import datetime
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from firebase_admin import firestore
from starlette.middleware.sessions import SessionMiddleware

from auth import exchange_token, get_current_user, init_auth
from services.tsv_service import generate_ruleset_tsv

# Load environment variables
load_dotenv()

# Constants for Speckle API
SPECKLE_SERVER_URL = os.getenv("SPECKLE_SERVER_URL", "https://app.speckle.systems")
PROJECTS_PER_PAGE = 5
MODELS_PER_PROJECT = 20
VERSIONS_PER_MODEL = 1

# GraphQL queries
PROJECTS_QUERY = """
query($projectsLimit: Int!, $modelsLimit: Int!, $versionsLimit: Int!, $modelsCursor: String, $projectsCursor: String) {
  activeUser {
    projects(limit: $projectsLimit, cursor: $projectsCursor) {
      totalCount
      cursor
      items {
        id
        name
        description
        models(limit: $modelsLimit, cursor: $modelsCursor) {
          totalCount
          cursor
          items {
            id
            name
            description
            previewUrl
            versions(limit: $versionsLimit) {
              items {
                sourceApplication
              }
            }
          }
        }
      }
    }
  }
}
"""

PROJECTS_SEARCH_QUERY = """
query($filter: UserProjectsFilter, $modelsLimit: Int!, $versionsLimit: Int!) {
  activeUser {
    projects(filter: $filter) {
      items {
        id
        name
        description
        models(limit: $modelsLimit) {
          totalCount
          items {
            id
            name
            description
            previewUrl
            versions(limit: $versionsLimit) {
              items {
                sourceApplication
              }
            }
          }
        }
      }
    }
  }
}
"""

# Initialize Firebase Admin and get Firestore client
db = firestore.client()

app = FastAPI()

# Add session middleware
app.add_middleware(
    SessionMiddleware, secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key")
)

# Mount static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Templates
templates = Jinja2Templates(directory="../frontend/templates")


@app.get("/auth/init")
async def auth_init(request: Request):
    """Initialize Speckle authentication"""
    return await init_auth(request)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback from Speckle"""
    return await exchange_token(request)


@app.get("/logout")
async def logout(request: Request):
    """Clear the session and redirect to home"""
    request.session.clear()
    return HTMLResponse(
        """
        <script>
            localStorage.removeItem('firebaseToken');
            window.location.href = '/';
        </script>
        """
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # print("=== Starting home function ===")
    user = await get_current_user(request)
    firebase_token = request.query_params.get("ft")

    if firebase_token:
        # print("Firebase token found in query params")
        # If we have a firebase token, inject it into localStorage
        return HTMLResponse(
            f"""
            <script>
                localStorage.setItem('firebaseToken', '{firebase_token}');
                window.location.href = '/';
            </script>
            """
        )

    if not user:
        # print("No user found, showing login page")
        return templates.TemplateResponse(
            "login.html", {"request": request, "title": "Model Checker", "user": user}
        )

    # print(f"User found: {user['id']}")

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        # print("No user token found, showing login page")
        return templates.TemplateResponse(
            "login.html", {"request": request, "title": "Model Checker", "user": None}
        )

    speckle_token = user_token.to_dict().get("speckleToken")
    # print("Got Speckle token")

    # Fetch projects from Speckle
    async with httpx.AsyncClient() as client:
        try:
            # print("=== Making request to Speckle ===")
            variables = {
                "projectsLimit": PROJECTS_PER_PAGE,
                "modelsLimit": MODELS_PER_PROJECT,
                "versionsLimit": VERSIONS_PER_MODEL,
                "projectsCursor": None,
                "modelsCursor": None,
            }
            # print(
            #     "Making request to Speckle with variables:",
            #     json.dumps(variables, indent=2),
            # )
            # print("Query:", PROJECTS_QUERY)

            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={"query": PROJECTS_QUERY, "variables": variables},
            )

            # print("=== Got response from Speckle ===")
            # print(f"Response status: {response.status_code}")
            # print(f"Response headers: {dict(response.headers)}")
            # print("Raw response:", response.text)

            if response.status_code != 200:
                error_content = response.text
                # print(f"Error response from Speckle: {error_content}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to fetch projects from Speckle: {error_content}",
                )

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response: {e}")
                print("Raw response was:", response.text)
                raise HTTPException(
                    status_code=500, detail="Invalid JSON response from Speckle"
                )

            # print(f"Response data keys: {data.keys()}")
            if "errors" in data:
                print(f"GraphQL errors: {json.dumps(data['errors'], indent=2)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"GraphQL errors: {json.dumps(data['errors'])}",
                )

            if "data" not in data or "activeUser" not in data["data"]:
                print(f"Unexpected response structure: {json.dumps(data, indent=2)}")
                raise HTTPException(
                    status_code=500, detail="Unexpected response structure from Speckle"
                )

            projects = data["data"]["activeUser"]["projects"]["items"]
            has_more_projects = (
                data["data"]["activeUser"]["projects"]["cursor"] is not None
            )
            next_projects_cursor = data["data"]["activeUser"]["projects"]["cursor"]

            # print("=== Successfully processed response ===")

            total_count = (
                data.get("data", {})
                .get("activeUser", {})
                .get("projects", {})
                .get("totalCount", 0)
            )

            # print(f"Total projects available: {total_count}")

            return templates.TemplateResponse(
                "project_list.html",
                {
                    "request": request,
                    "title": "Model Checker",
                    "user": user,
                    "projects": projects,
                    "has_more_projects": has_more_projects,
                    "next_projects_cursor": next_projects_cursor,
                },
            )

        except Exception as e:
            import traceback

            print("=== Error in home function ===")
            print("Error type:", type(e).__name__)
            print("Error message:", str(e))
            print("Full traceback:")
            print(traceback.format_exc())

            return templates.TemplateResponse(
                "project_list.html",
                {
                    "request": request,
                    "title": "Model Checker",
                    "user": user,
                    "projects": [],
                    "has_more_projects": False,
                    "next_projects_cursor": None,
                },
            )


@app.get("/rulesets", response_class=HTMLResponse)
async def list_rulesets(request: Request):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    rulesets = db.collection("rulesets").where("user_id", "==", user["id"]).stream()
    ruleset_list = []
    for doc in rulesets:
        data = doc.to_dict()
        data["id"] = doc.id
        ruleset_list.append(data)
    return templates.TemplateResponse(
        "rulesets.html", {"request": request, "rulesets": ruleset_list, "user": user}
    )


@app.get("/rulesets/new", response_class=HTMLResponse)
async def new_ruleset(request: Request):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    return templates.TemplateResponse(
        "ruleset_form.html", {"request": request, "ruleset": None, "user": user}
    )


@app.get("/rulesets/{ruleset_id}/edit", response_class=HTMLResponse)
async def edit_ruleset(request: Request, ruleset_id: str):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    doc = db.collection("rulesets").document(ruleset_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset = doc.to_dict()
    if ruleset.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset["id"] = doc.id
    return templates.TemplateResponse(
        "ruleset_form.html", {"request": request, "ruleset": ruleset, "user": user}
    )


@app.post("/rulesets")
async def create_ruleset(request: Request):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    form_data = await request.form()
    project_id = form_data.get("project_id")

    # Generate TSV content
    tsv_content = "Property\tPredicate\tValue\tMessage\tSeverity\n"

    ruleset_data = {
        "name": form_data.get("name"),
        "description": form_data.get("description", ""),
        "rules": [],
        "created_at": datetime.utcnow(),
        "user_id": user["id"],
        "project_id": project_id,
        "tsv_content": tsv_content,  # Store the TSV content
    }

    # Create the ruleset and get its ID
    ruleset_ref = db.collection("rulesets").add(ruleset_data)
    ruleset_id = ruleset_ref[1].id

    # If it's an HTMX request, return the rules list partial
    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/rules_list.html",
            {
                "request": request,
                "ruleset": {"id": ruleset_id, **ruleset_data},
                "rules": [],
            },
        )

    # Otherwise redirect to the ruleset detail page
    return RedirectResponse(
        url=f"/projects/{project_id}/rules/{ruleset_id}", status_code=303
    )


@app.post("/rulesets/{ruleset_id}")
async def update_ruleset(request: Request, ruleset_id: str):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    doc = db.collection("rulesets").document(ruleset_id).get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset = doc.to_dict()
    if ruleset.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    form_data = await request.form()
    try:
        rules = json.loads(form_data.get("rules"))
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in rules field")

    ruleset_data = {
        "name": form_data.get("name"),
        "description": form_data.get("description"),
        "rules": rules,
        "updated_at": datetime.utcnow(),
    }

    db.collection("rulesets").document(ruleset_id).update(ruleset_data)
    return HTMLResponse(
        """
        <script>
            window.location.href = '/rulesets';
        </script>
        """
    )


@app.get("/projects", response_class=HTMLResponse)
async def get_projects(
    request: Request, projects_cursor: str = None, models_cursor: str = None
):
    # print(f"Projects cursor: {projects_cursor}")

    # print(request.query_params)

    """Get projects list with pagination support for both projects and models"""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        return HTMLResponse(status_code=401)

    speckle_token = user_token.to_dict().get("speckleToken")

    # Fetch projects from Speckle
    async with httpx.AsyncClient() as client:
        try:
            # Log the request details
            variables = {
                "projectsLimit": PROJECTS_PER_PAGE,
                "modelsLimit": MODELS_PER_PROJECT,
                "versionsLimit": VERSIONS_PER_MODEL,
                "projectsCursor": projects_cursor,
                "modelsCursor": models_cursor,
            }
            # print(
            #     "Making request to Speckle with variables:",
            #     json.dumps(variables, indent=2),
            # )

            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={"query": PROJECTS_QUERY, "variables": variables},
            )

            # Log the raw response for debugging
            # print("Raw response from Speckle:", response.text)

            response.raise_for_status()
            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                print("GraphQL errors:", json.dumps(data["errors"], indent=2))
                if request.headers.get("HX-Request"):
                    return templates.TemplateResponse(
                        "partials/project_list_content.html",
                        {
                            "request": request,
                            "projects": [],
                            "has_more_projects": False,
                            "next_projects_cursor": None,
                        },
                    )
                return templates.TemplateResponse(
                    "project_list.html",
                    {
                        "request": request,
                        "user": user,
                        "projects": [],
                        "has_more_projects": False,
                        "next_projects_cursor": None,
                    },
                )

            # Extract projects from response
            projects = (
                data.get("data", {})
                .get("activeUser", {})
                .get("projects", {})
                .get("items", [])
            )
            has_more_projects = bool(
                data.get("data", {})
                .get("activeUser", {})
                .get("projects", {})
                .get("cursor")
            )
            next_projects_cursor = (
                data.get("data", {})
                .get("activeUser", {})
                .get("projects", {})
                .get("cursor")
            )

            # print(f"Next projects cursor: {next_projects_cursor}")

            # Return appropriate template based on request type
            if request.headers.get("HX-Request"):
                content = templates.get_template(
                    "partials/project_list_content.html"
                ).render(
                    {
                        "request": request,
                        "projects": projects,
                        "has_more_projects": has_more_projects,
                        "next_projects_cursor": next_projects_cursor,
                    }
                )

                content += templates.get_template("partials/load_more_oob.html").render(
                    {
                        "has_more_projects": has_more_projects,
                        "next_projects_cursor": next_projects_cursor,
                    }
                )
                response = HTMLResponse(content)
                return response
            return templates.TemplateResponse(
                "project_list.html",
                {
                    "request": request,
                    "user": user,
                    "projects": projects,
                    "has_more_projects": has_more_projects,
                    "next_projects_cursor": next_projects_cursor,
                },
            )

        except Exception as e:
            print(f"Error in get_projects: {str(e)}")
            if request.headers.get("HX-Request"):
                return templates.TemplateResponse(
                    "partials/project_list_content.html",
                    {
                        "request": request,
                        "projects": [],
                        "has_more_projects": False,
                        "next_projects_cursor": None,
                    },
                )
            return templates.TemplateResponse(
                "project_list.html",
                {
                    "request": request,
                    "user": user,
                    "projects": [],
                    "has_more_projects": False,
                    "next_projects_cursor": None,
                },
            )


@app.get("/projects/search", response_class=HTMLResponse)
async def search_projects(request: Request, search: str = None):
    """Search projects by name or description"""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        return HTMLResponse(status_code=401)

    speckle_token = user_token.to_dict().get("speckleToken")

    # If search is empty or None, use the regular projects query
    if not search:
        return await get_projects(request)

    # Fetch projects from Speckle
    async with httpx.AsyncClient() as client:
        try:
            # Log the request details
            variables = {
                "modelsLimit": MODELS_PER_PROJECT,
                "versionsLimit": VERSIONS_PER_MODEL,
                "filter": {"search": search},
            }
            # print(
            #     "Making search request to Speckle with variables:",
            #     json.dumps(variables, indent=2),
            # )

            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={"query": PROJECTS_SEARCH_QUERY, "variables": variables},
            )

            # Log the raw response for debugging
            # print("Raw response from Speckle:", response.text)

            response.raise_for_status()
            data = response.json()

            # Check for GraphQL errors
            if "errors" in data:
                print("GraphQL errors:", json.dumps(data["errors"], indent=2))
                return templates.TemplateResponse(
                    "partials/project_list_content.html",
                    {
                        "request": request,
                        "projects": [],
                        "has_more_projects": False,
                        "next_projects_cursor": None,
                    },
                )

            # Extract projects from response
            projects = (
                data.get("data", {})
                .get("activeUser", {})
                .get("projects", {})
                .get("items", [])
            )

            # Return both the project list content and the load more container state

            content = templates.get_template(
                "partials/project_list_content.html"
            ).render(
                {
                    "request": request,
                    "projects": projects,
                    "has_more_projects": False,
                    "next_projects_cursor": None,
                }
            )

            # Hide the load more button
            content += templates.get_template("partials/load_more_oob.html").render(
                {
                    "has_more_projects": False,
                    "next_projects_cursor": None,
                }
            )

            response = HTMLResponse(content)
            return response

        except Exception as e:
            print(f"Error in search_projects: {str(e)}")
            return templates.TemplateResponse(
                "partials/project_list_content.html",
                {
                    "request": request,
                    "projects": [],
                    "has_more_projects": False,
                    "next_projects_cursor": None,
                },
            )


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_details(request: Request, project_id: str):
    """Get details and rulesets for a specific project"""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        return HTMLResponse(status_code=401)

    speckle_token = user_token.to_dict().get("speckleToken")

    # Fetch project details from Speckle
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={
                    "query": """
                    query($projectId: String!) {
                        project(id: $projectId) {
                            id
                            name
                            description
                        }
                    }
                    """,
                    "variables": {"projectId": project_id},
                },
            )

            response.raise_for_status()
            data = response.json()

            if "errors" in data or not data.get("data", {}).get("project"):
                print(
                    "Project not found or GraphQL errors:",
                    json.dumps(data.get("errors", []), indent=2),
                )
                return templates.TemplateResponse(
                    "project_not_found.html", {"request": request, "user": user}
                )

            project = data.get("data", {}).get("project")

            # print(f"Project: {project['id']}")

            # Get rulesets for this project
            rulesets = (
                db.collection("rulesets")
                .where("user_id", "==", user["id"])
                .where("project_id", "==", project["id"])
                .stream()
            )

            ruleset_list = []
            for doc in rulesets:
                data = doc.to_dict()
                data["id"] = doc.id
                data["rules"] = list(
                    db.collection("rulesets")
                    .document(doc.id)
                    .collection("rules")
                    .stream()
                )
                ruleset_list.append(data)

            return templates.TemplateResponse(
                "project_rulesets.html",
                {
                    "request": request,
                    "user": user,
                    "project": project,
                    "rulesets": ruleset_list,
                },
            )

        except Exception as e:
            print(f"Error in project_details: {str(e)}")
            return templates.TemplateResponse(
                "project_not_found.html", {"request": request, "user": user}
            )


@app.get("/projects/{project_id}/new", response_class=HTMLResponse)
async def new_project_ruleset(request: Request, project_id: str):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        return HTMLResponse(status_code=401)

    speckle_token = user_token.to_dict().get("speckleToken")

    # Fetch project details from Speckle
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={
                    "query": """
                    query($projectId: String!) {
                        project(id: $projectId) {
                            id
                            name
                            description
                        }
                    }
                    """,
                    "variables": {"projectId": project_id},
                },
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data or not data.get("data", {}).get("project"):
                print(
                    "Project not found or GraphQL errors:",
                    json.dumps(data.get("errors", []), indent=2),
                )
                return templates.TemplateResponse(
                    "project_not_found.html", {"request": request, "user": user}
                )
            project = data.get("data", {}).get("project")
            return templates.TemplateResponse(
                "ruleset_form.html",
                {"request": request, "ruleset": None, "user": user, "project": project},
            )
        except Exception as e:
            print(f"Error in new_project_ruleset: {str(e)}")
            return templates.TemplateResponse(
                "project_not_found.html", {"request": request, "user": user}
            )


@app.get("/rulesets/{ruleset_id}/rules/new", response_class=HTMLResponse)
async def new_rule_form(request: Request, ruleset_id: str):
    # Render the rule form partial (empty for new rule)
    return templates.TemplateResponse(
        "partials/rule_form.html",
        {
            "request": request,
            "ruleset": {"id": ruleset_id},
            "rule": None,
        },
    )


def clean_conditions(conditions):
    """Remove any blank conditions and enforce WHERE/CHECK pattern."""
    # Remove any conditions with empty propertyName
    cleaned = [c for c in conditions if c.get("propertyName", "").strip()]

    # If no valid conditions, return empty list
    if not cleaned:
        return []

    # Enforce WHERE/CHECK pattern
    if len(cleaned) == 1:
        # Single condition must be WHERE
        cleaned[0]["logic"] = "WHERE"
    else:
        # Multiple conditions:
        # First must be WHERE
        cleaned[0]["logic"] = "WHERE"
        # Last must be CHECK
        cleaned[-1]["logic"] = "CHECK"
        # All middle conditions must be AND
        for c in cleaned[1:-1]:
            c["logic"] = "AND"

    return cleaned


@app.post("/rulesets/{ruleset_id}/rules")
async def add_rule(request: Request, ruleset_id: str):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    form_data = await request.form()
    # Parse conditions from form data
    import re

    conditions = []
    for key in form_data:
        m = re.match(r"conditions\[(\d+)\]\[(\w+)\]", key)
        if m:
            idx, field = int(m.group(1)), m.group(2)
            while len(conditions) <= idx:
                conditions.append({})
            conditions[idx][field] = form_data[key]

    # Clean and validate conditions
    conditions = clean_conditions(conditions)

    # Create rule document
    # Get current max order for this ruleset
    rules_ref = db.collection("rulesets").document(ruleset_id).collection("rules")

    # Count existing rules to determine order
    existing_rules = list(rules_ref.stream())
    next_order = len(existing_rules) + 1

    rule_data = {
        "conditions": conditions,
        "message": form_data.get("message"),
        "auto_generated_message": form_data.get("auto_generated_message"),
        "severity": form_data.get("severity"),
        "order": next_order,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    # Get the ruleset
    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()
    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset_data["id"] = ruleset_id

    # Generate rule ID
    rule_id = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(20)
    )

    # Add rule to ruleset
    rules_ref.document(rule_id).set(rule_data)

    # Fetch all rules from the subcollection
    rules_query = rules_ref.order_by("order").stream()
    rules = [doc.to_dict() | {"id": doc.id} for doc in rules_query]

    ruleset_ref.update({"updatedAt": firestore.SERVER_TIMESTAMP})

    # Return the updated rules.html partial
    return templates.TemplateResponse(
        "partials/ruleset_rules.html",
        {
            "request": request,
            "ruleset": ruleset_data,
            "rules": rules,
        },
    )


def generate_ruleset_hash(project_id: str, ruleset_id: str) -> str:
    """Generate a unique hash for a ruleset that combines project and ruleset IDs."""
    combined = f"{project_id}:{ruleset_id}"
    hash_bytes = hashlib.sha256(combined.encode()).digest()
    # Use base64url encoding (URL-safe) and remove padding
    return base64.urlsafe_b64encode(hash_bytes).decode().rstrip("=")


@app.get("/r/{ruleset_hash}/tsv")
async def get_ruleset_tsv(request: Request, ruleset_hash: str):
    """Get TSV content for a ruleset using its hash. No authentication required."""
    # Get all rulesets
    rulesets = db.collection("rulesets").stream()

    # Find the matching ruleset by comparing hashes
    matching_ruleset = None
    for ruleset in rulesets:
        ruleset_data = ruleset.to_dict()
        current_hash = generate_ruleset_hash(
            ruleset_data.get("project_id", ""), ruleset.id
        )
        if current_hash == ruleset_hash:
            matching_ruleset = ruleset
            break

    if not matching_ruleset:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = matching_ruleset.to_dict()
    ruleset_data["id"] = matching_ruleset.id

    # Get all rules for this ruleset
    rules_query = (
        db.collection("rulesets")
        .document(matching_ruleset.id)
        .collection("rules")
        .order_by("order")
        .stream()
    )
    rules = [doc.to_dict() | {"id": doc.id} for doc in rules_query]

    # Generate TSV content
    tsv_content, filename = generate_ruleset_tsv(ruleset_data, rules)

    # Return the TSV content with appropriate headers
    return Response(
        content=tsv_content,
        media_type="text/tab-separated-values",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/projects/{project_id}/rulesets")
async def create_project_ruleset(request: Request, project_id: str):
    """Create a new ruleset for a project."""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    form_data = await request.form()
    name = form_data.get("name")
    description = form_data.get("description", "")

    # Generate TSV content
    tsv_content = "Property\tPredicate\tValue\tMessage\tSeverity\n"

    ruleset_data = {
        "name": name,
        "description": description,
        "rules": [],
        "created_at": datetime.utcnow(),
        "user_id": user["id"],
        "project_id": project_id,
        "tsv_content": tsv_content,
    }

    # Create the ruleset and get its ID
    ruleset_ref = db.collection("rulesets").add(ruleset_data)
    ruleset_id = ruleset_ref[1].id

    # If it's an HTMX request from the name field blur, return the form in edit mode
    if (
        request.headers.get("HX-Request")
        and request.headers.get("X-Event-Type") == "blur"
    ):
        # Get project details
        user_token = db.collection("userTokens").document(user["id"]).get()
        speckle_token = user_token.to_dict().get("speckleToken")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={
                    "query": """
                    query($projectId: String!) {
                        project(id: $projectId) {
                            id
                            name
                            description
                        }
                    }
                    """,
                    "variables": {"projectId": project_id},
                },
            )
            response.raise_for_status()
            data = response.json()
            project = data.get("data", {}).get("project")

        # Return the form in edit mode
        return templates.TemplateResponse(
            "partials/ruleset_form_content.html",
            {
                "request": request,
                "ruleset": {"id": ruleset_id, **ruleset_data},
                "user": user,
                "project": project,
                "is_edit": True,
            },
        )

    # Otherwise redirect to the project page
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.get("/api/rulesets/{ruleset_id}/hash")
async def get_ruleset_hash(
    ruleset_id: str, project_id: str, user: dict = Depends(get_current_user)
):
    """Generate a hash for a ruleset."""
    ruleset = db.collection("rulesets").document(ruleset_id).get()
    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if (
        ruleset_data["user_id"] != user["id"]
        or ruleset_data["project_id"] != project_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to access this ruleset"
        )

    hash_value = generate_ruleset_hash(project_id, ruleset_id)
    return {"hash": hash_value}


@app.get("/projects/{project_id}/rulesets/{ruleset_id}", response_class=HTMLResponse)
async def edit_project_ruleset(request: Request, project_id: str, ruleset_id: str):
    """Get the edit form for a specific ruleset in a project."""

    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get user's Speckle token
    user_token = db.collection("userTokens").document(user["id"]).get()
    if not user_token.exists:
        return HTMLResponse(status_code=401)

    speckle_token = user_token.to_dict().get("speckleToken")

    # Fetch project details from Speckle
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                urljoin(SPECKLE_SERVER_URL, "/graphql"),
                headers={"Authorization": f"Bearer {speckle_token}"},
                json={
                    "query": """
                    query($projectId: String!) {
                        project(id: $projectId) {
                            id
                            name
                            description
                        }
                    }
                    """,
                    "variables": {"projectId": project_id},
                },
            )
            response.raise_for_status()
            data = response.json()
            if "errors" in data or not data.get("data", {}).get("project"):
                print(
                    "Project not found or GraphQL errors:",
                    json.dumps(data.get("errors", []), indent=2),
                )
                return templates.TemplateResponse(
                    "project_not_found.html", {"request": request, "user": user}
                )
            project = data.get("data", {}).get("project")

            # Get the ruleset
            ruleset_ref = db.collection("rulesets").document(ruleset_id)
            ruleset = ruleset_ref.get()
            if not ruleset.exists:
                raise HTTPException(status_code=404, detail="Ruleset not found")

            ruleset_data = ruleset.to_dict()
            if (
                ruleset_data.get("user_id") != user["id"]
                or ruleset_data.get("project_id") != project_id
            ):
                raise HTTPException(
                    status_code=403, detail="Not authorized to edit this ruleset"
                )

            ruleset_data["id"] = ruleset_id
            # Fetch rules from subcollection
            rules_query = (
                db.collection("rulesets")
                .document(ruleset_id)
                .collection("rules")
                .order_by("order")
                .stream()
            )
            rules = [doc.to_dict() | {"id": doc.id} for doc in rules_query]
            ruleset_data["rules"] = rules

            return templates.TemplateResponse(
                "ruleset_form.html",
                {
                    "request": request,
                    "ruleset": ruleset_data,
                    "user": user,
                    "project": project,
                    "is_edit": True,
                    "rules": rules,
                },
            )
        except Exception as e:
            print(f"Error in edit_project_ruleset: {str(e)}")
            return templates.TemplateResponse(
                "project_not_found.html", {"request": request, "user": user}
            )


@app.post("/projects/{project_id}/rulesets/{ruleset_id}")
async def update_project_ruleset(request: Request, project_id: str, ruleset_id: str):
    """Update an existing ruleset."""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get the ruleset
    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()
    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if (
        ruleset_data.get("user_id") != user["id"]
        or ruleset_data.get("project_id") != project_id
    ):
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset_data["id"] = ruleset_id

    # Get form data
    form_data = await request.form()

    # Update the ruleset
    update_data = {
        "name": form_data.get("name"),
        "description": form_data.get("description", ""),
        "updated_at": datetime.utcnow(),
    }

    # Update the ruleset
    ruleset_ref.update(update_data)

    # Redirect back to the project page
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)


@app.get("/rulesets/{ruleset_id}/rules/condition_row", response_class=HTMLResponse)
async def condition_row(request: Request, ruleset_id: str):
    """Render a new condition row partial for HTMX dynamic addition."""

    keys_list = list(request.query_params.keys())

    # count the number keys starting with conditions
    index = sum(1 for key in keys_list if key.startswith("conditions"))

    # print(f"Index: {index}")

    return templates.TemplateResponse(
        "partials/condition_row.html",
        {
            "request": request,
            "ruleset_id": ruleset_id,
            "condition": None,
            "index": index,
        },
    )


@app.get("/rulesets/{ruleset_id}/rules/{rule_id}/edit", response_class=HTMLResponse)
async def edit_rule(request: Request, ruleset_id: str, rule_id: str):
    """Get the edit form for a specific rule."""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get the ruleset
    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()
    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    # Get the rule
    rule_ref = ruleset_ref.collection("rules").document(rule_id)
    rule = rule_ref.get()
    if not rule.exists:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule_data = rule.to_dict()
    rule_data["id"] = rule_id

    return templates.TemplateResponse(
        "partials/edit_rule_form.html",
        {
            "request": request,
            "ruleset": {"id": ruleset_id, **ruleset_data},
            "rule": rule_data,
        },
    )


@app.post("/rulesets/{ruleset_id}/rules/{rule_id}")
async def update_rule(request: Request, ruleset_id: str, rule_id: str):
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    form_data = await request.form()
    # Parse conditions from form data
    import re

    conditions = []
    for key in form_data:
        m = re.match(r"conditions\[(\d+)\]\[(\w+)\]", key)
        if m:
            idx, field = int(m.group(1)), m.group(2)
            while len(conditions) <= idx:
                conditions.append({})
            conditions[idx][field] = form_data[key]

    # Clean and validate conditions
    conditions = clean_conditions(conditions)

    # Get the ruleset
    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()
    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")
    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset_data["id"] = ruleset_id

    # Update rule document
    rule_data = {
        "conditions": conditions,
        "message": form_data.get("message"),
        "auto_generated_message": form_data.get("auto_generated_message"),
        "severity": form_data.get("severity"),
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    # Update rule in ruleset
    rules_ref = db.collection("rulesets").document(ruleset_id).collection("rules")
    rules_ref.document(rule_id).update(rule_data)

    # Fetch all rules from the subcollection
    rules_query = rules_ref.order_by("order").stream()
    rules = [doc.to_dict() | {"id": doc.id} for doc in rules_query]

    # Return the rules list partial
    return templates.TemplateResponse(
        "partials/ruleset_rules.html",
        {
            "request": request,
            "ruleset": ruleset_data,
            "rules": rules,
        },
    )


@app.get("/rulesets/{ruleset_id}/rules/{rule_id}/delete", response_class=HTMLResponse)
async def confirm_delete_rule(
    ruleset_id: str,
    rule_id: str,
    request: Request,
):
    """Show delete confirmation dialog for a rule."""

    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()

    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset_data["id"] = ruleset_id

    rule_ref = ruleset_ref.collection("rules").document(rule_id)
    rule = rule_ref.get()

    if not rule.exists:
        raise HTTPException(status_code=404, detail="Rule not found")

    return templates.TemplateResponse(
        "partials/delete_rule_confirm.html",
        {"request": request, "ruleset": ruleset_data, "rule": rule.to_dict()},
    )


@app.delete("/api/rulesets/{ruleset_id}/rules/{rule_id}")
async def delete_rule(
    request: Request,
    ruleset_id: str,
    rule_id: str,
):
    """Delete a rule from a ruleset."""

    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()

    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    ruleset_data["id"] = ruleset_id

    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    rule_ref = ruleset_ref.collection("rules").document(rule_id)
    rule = rule_ref.get()

    if not rule.exists:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Delete the rule
    rule_ref.delete()

    rules_ref = ruleset_ref.collection("rules")

    rules_query = rules_ref.order_by("order").stream()

    batch = db.batch()
    for index, rule in enumerate(rules_query):
        rule_ref = rules_ref.document(rule.id)
        batch.update(rule_ref, {"order": index + 1})

    batch.commit()

    # Get all rules to return updated list
    rules = [
        doc.to_dict() | {"id": doc.id}
        for doc in ruleset_ref.collection("rules").order_by("order").stream()
    ]

    return templates.TemplateResponse(
        "partials/ruleset_rules.html",
        {"request": request, "ruleset": ruleset_data, "rules": rules},
    )


@app.post("/api/rulesets/{ruleset_id}/rules/{rule_id}/reorder")
async def reorder_rule(
    request: Request,
    ruleset_id: str,
    rule_id: str,
    direction: str,  # "up" or "down"
):
    """Reorder a rule within its ruleset."""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()

    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this ruleset"
        )

    ruleset_data["id"] = ruleset_id

    # Get all rules ordered by their current order
    rules_ref = ruleset_ref.collection("rules")
    rules_query = rules_ref.order_by("order").stream()
    rules = [(doc.id, doc.to_dict()) for doc in rules_query]

    # Find the current rule's index
    current_index = next(
        (i for i, (rid, _) in enumerate(rules) if rid == rule_id), None
    )
    if current_index is None:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Calculate the target index
    if direction == "up" and current_index > 0:
        target_index = current_index - 1
    elif direction == "down" and current_index < len(rules) - 1:
        target_index = current_index + 1
    else:
        # Can't move further in this direction
        return templates.TemplateResponse(
            "partials/ruleset_rules.html",
            {
                "request": request,
                "ruleset": ruleset_data,
                "rules": [{"id": rid, **rdata} for rid, rdata in rules],
            },
        )

    # Swap the rules
    rules[current_index], rules[target_index] = (
        rules[target_index],
        rules[current_index],
    )

    # Update the order values in Firestore
    batch = db.batch()
    for i, (rid, rdata) in enumerate(rules):
        rule_ref = rules_ref.document(rid)
        batch.update(rule_ref, {"order": i + 1})
    batch.commit()

    # Return the updated rules list
    return templates.TemplateResponse(
        "partials/ruleset_rules.html",
        {
            "request": request,
            "ruleset": ruleset_data,
            "rules": [{"id": rid, **rdata} for rid, rdata in rules],
        },
    )


@app.delete("/api/rulesets/{ruleset_id}/condition-row/{index}")
async def delete_condition_row(request: Request, ruleset_id: str, index: int):
    """Delete a condition row from the form."""
    # This is just a UI operation, no need to check auth or persist anything
    return HTMLResponse("")


@app.post("/api/rulesets/{ruleset_id}/condition-row/{index}/reorder")
async def reorder_condition_row(
    request: Request, ruleset_id: str, index: int, direction: str
):
    """Reorder a condition row within the form."""
    # This is just a UI operation, no need to check auth or persist anything
    # The actual order will be saved when the rule is saved
    return HTMLResponse("")


# Chrome DevTools Probe - it doesn't do anything handling, but it prevents logs
# filling with 400 errors
@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_probe():
    return JSONResponse(content={"devtools": False})


@app.delete("/api/rulesets/{ruleset_id}")
async def delete_ruleset(request: Request, ruleset_id: str):
    """Delete a ruleset and all its rules."""
    user = await get_current_user(request)
    if not user:
        return HTMLResponse(status_code=401)

    # Get the ruleset
    ruleset_ref = db.collection("rulesets").document(ruleset_id)
    ruleset = ruleset_ref.get()

    if not ruleset.exists:
        raise HTTPException(status_code=404, detail="Ruleset not found")

    ruleset_data = ruleset.to_dict()
    if ruleset_data.get("user_id") != user["id"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to delete this ruleset"
        )

    # Delete all rules in the subcollection
    rules_ref = ruleset_ref.collection("rules")
    for rule in rules_ref.stream():
        rule.reference.delete()

    # Delete the ruleset
    ruleset_ref.delete()

    return HTMLResponse("")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
