# cloudrun/src/speckle.py - Speckle API Client
import requests
from .database import get_user_token


def get_user_projects(app, user_id):
    """Get user's Speckle projects"""
    speckle_token = get_user_token(app, user_id)
    if not speckle_token:
        return []

    query = """
    query {
      activeUser {
        projects(limit: 10) {
          items {
            id
            name
            description
            models {
              totalCount
              items {
                id
                name
                previewUrl
                description
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        f"{app.env['SPECKLE_SERVER_URL']}/graphql",
        headers={"Authorization": f"Bearer {speckle_token}"},
        json={"query": query},
    )

    if response.status_code != 200:
        return []

    data = response.json()
    if "errors" not in data:
        return data["data"]["activeUser"]["projects"]["items"]

    return []


def get_project_details(app, user_id, project_id):
    """Get details for a specific project"""
    speckle_token = get_user_token(app, user_id)
    if not speckle_token:
        return None

    query = """
    query ProjectDetails($id: String!) {
      project(id: $id) {
        id
        name
        description
        createdAt
        models {
          totalCount
          items {
            id
            name
            createdAt
          }
        }
      }
    }
    """

    variables = {"id": project_id}

    response = requests.post(
        f"{app.env['SPECKLE_SERVER_URL']}/graphql",
        headers={"Authorization": f"Bearer {speckle_token}"},
        json={"query": query, "variables": variables},
    )

    if response.status_code != 200:
        return None

    data = response.json()
    if "errors" not in data:
        return data["data"]["project"]

    return None
