import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SpeckleAPI:
    """
    Synchronous wrapper for interacting with the Speckle API using HTTP requests.
    """

    def __init__(self, token: str, host: str = "https://app.speckle.systems"):
        self.token = token
        self.host = host
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def run_graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        url = f"{self.host}/graphql"
        payload = {"query": query, "variables": variables or {}}

        try:
            response = requests.post(url, headers=self.headers, json=payload)
            if not response.ok:
                print(f"Status: {response.status_code}")
                print(f"Response text: {response.text}")
            response.raise_for_status()
            return response.json()["data"]
        except Exception as e:
            logger.error(f"GraphQL query error: {str(e)}")
            raise

    def get_user_projects_with_models(self) -> List[Dict]:
        query = """
          query UserProjects ($filter: UserProjectsFilter) {
              activeUser {
                projects(filter: $filter, limit: 10) {
                  items {
                    id
                    name
                    role
                    models {
                      totalCount
                      items {
                        versions {
                          items {
                            sourceApplication
                          }
                        }
                        name
                        id
                        description
                        previewUrl
                        updatedAt
                      }
                    }
                    updatedAt
                    description
                  }
                  totalCount
                }
              }
            }
            """
        variables = {"filter": {"onlyWithRoles": ["stream:owner"]}}

        try:
            logger.info("Fetching user projects with models")
            data = self.run_graphql_query(query, variables)

            if (
                "activeUser" in data
                and "projects" in data["activeUser"]
                and "items" in data["activeUser"]["projects"]
            ):
                projects = data["activeUser"]["projects"]["items"]
                logger.info(f"Found {len(projects)} projects")

                # Log some info about the first project's models if available
                if projects and "models" in projects[0]:
                    model_count = projects[0]["models"].get("totalCount", 0)
                    logger.info(f"First project has {model_count} models")

                return projects
            else:
                logger.warning(f"Unexpected API response structure: {data}")
                return []
        except Exception as e:
            logger.exception(f"Error getting user projects: {str(e)}")
            return []

    def get_project_details(self, project_id: str) -> Dict:
        project_query = """
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
        data = self.run_graphql_query(project_query, variables)
        return data["project"]

    def get_model_versions(self, model_id: str) -> List[Dict]:
        versions_query = """
        query GetModelVersions($modelId: String!) {
            model(id: $modelId) {
                versions {
                    items {
                        id
                        message
                        createdAt
                        author {
                            id
                            name
                        }
                    }
                }
            }
        }
        """
        variables = {"modelId": model_id}
        data = self.run_graphql_query(versions_query, variables)
        return data["model"]["versions"]["items"]

    def create_comment(self, stream_id: str, object_id: str, message: str) -> Dict:
        mutation = """
        mutation CreateComment($input: CreateCommentInput!) {
            commentCreate(input: $input) {
                id
                message
                createdAt
            }
        }
        """
        variables = {
            "input": {
                "streamId": stream_id,
                "resources": [{"resourceId": object_id}],
                "message": message,
            }
        }
        data = self.run_graphql_query(mutation, variables)
        return data["commentCreate"]

    def search_objects(self, stream_id: str, query_string: str) -> List[Dict]:
        search_query = """
        query SearchObjects($streamId: String!, $search: String!) {
            stream(id: $streamId) {
                objectSearch(query: $search) {
                    id
                    speckleType
                }
            }
        }
        """
        variables = {"streamId": stream_id, "search": query_string}
        data = self.run_graphql_query(search_query, variables)
        return data["stream"]["objectSearch"]

    def get_version_objects(self, stream_id: str, object_id: str) -> Dict:
        """
        This replaces the operations.receive() call by doing a GET to the `/objects/{streamId}/{objectId}` endpoint.
        """
        url = f"{self.host}/api/streams/{stream_id}/objects/{object_id}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(
                f"Error fetching version objects for stream {stream_id} object {object_id}: {str(e)}"
            )
            raise


# Helper functions to instantiate and use easily:
def get_user_projects(token: str, host: str = "https://app.speckle.systems"):
    """
    Helper function to get user projects with models.

    Args:
        token (str): Speckle auth token
        host (str): Speckle server URL

    Returns:
        list: List of project objects
    """
    try:
        api = SpeckleAPI(token=token, host=host)
        projects = api.get_user_projects_with_models()

        # Log info for debugging
        if projects:
            print(f"Found {len(projects)} projects")
            if len(projects) > 0:
                print(f"First project name: {projects[0].get('name')}")

        return projects  # Return the actual projects data, not the function
    except Exception as e:
        print(f"Error in get_user_projects: {str(e)}")
        # Return empty list on error so template can still render
        return []


def get_project_details(
    token: str, project_id: str, host: str = "https://app.speckle.systems"
) -> Dict:
    api = SpeckleAPI(token=token, host=host)
    return api.get_project_details(project_id)
