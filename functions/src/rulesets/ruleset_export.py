import aiohttp
import json

async def get_user_projects(token):
    """
    Fetch all projects the user has access to via the Speckle API.
    
    Args:
        token (str): Speckle authentication token
        
    Returns:
        list: List of project objects
    """
    # GraphQL query to fetch user projects
    query = """
    query {
      activeUser {
        id
        name
        projectsPage(limit: 100) {
          items {
            id
            name
            description
            updatedAt
          }
        }
      }
    }
    """
    
    # Make the API request
    projects = await execute_speckle_query(query, token)
    
    # Extract and return projects from the response
    try:
        return projects['data']['activeUser']['projectsPage']['items']
    except (KeyError, TypeError):
        return []

async def get_project_details(token, project_id):
    """
    Fetch detailed information about a specific project via the Speckle API.
    
    Args:
        token (str): Speckle authentication token
        project_id (str): Project ID to fetch
        
    Returns:
        dict: Project details
    """
    # GraphQL query to fetch project details
    query = """
    query($projectId: String!) {
      project(id: $projectId) {
        id
        name
        description
        visibility
        updatedAt
        createdAt
        models {
          totalCount
          items {
            id
            name
            description
          }
        }
        collaborators {
          role
          user {
            id
            name
            avatar
          }
        }
      }
    }
    """
    
    # Make the API request with variables
    variables = {"projectId": project_id}
    result = await execute_speckle_query(query, token, variables)
    
    # Extract and return project from the response
    try:
        return result['data']['project']
    except (KeyError, TypeError):
        return None

async def get_model_objects(token, model_id):
    """
    Fetch objects for a specific model via the Speckle API.
    
    Args:
        token (str): Speckle authentication token
        model_id (str): Model ID to fetch objects from
        
    Returns:
        list: List of objects in the model
    """
    # GraphQL query to fetch model objects
    query = """
    query($modelId: String!) {
      model(id: $modelId) {
        id
        name
        commits(limit: 1) {
          items {
            id
            referencedObject {
              id
              speckleType
              children {
                totalCount
                cursor
                objects {
                  id
                  speckleType
                }
              }
            }
          }
        }
      }
    }
    """
    
    # Make the API request with variables
    variables = {"modelId": model_id}
    result = await execute_speckle_query(query, token, variables)
    
    # Extract and return objects from the response
    try:
        commit = result['data']['model']['commits']['items'][0]
        referenced_object = commit['referencedObject']
        children = referenced_object['children']['objects']
        return children
    except (KeyError, TypeError, IndexError):
        return []

async def execute_speckle_query(query, token, variables=None):
    """
    Execute a GraphQL query against the Speckle API.
    
    Args:
        query (str): GraphQL query
        token (str): Speckle authentication token
        variables (dict, optional): Query variables
        
    Returns:
        dict: Response data
    """
    url = "https://app.speckle.systems/graphql"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    payload = {
        "query": query
    }
    
    if variables:
        payload["variables"] = variables
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                response_text = await response.text()
                raise Exception(f"Speckle API error: {response.status} - {response_text}")