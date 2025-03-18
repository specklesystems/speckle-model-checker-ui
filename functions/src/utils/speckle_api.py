from typing import Dict, List, Optional, Any

from specklepy.api.client import SpeckleClient
from specklepy.api import operations
from specklepy.transports.server import ServerTransport

class SpeckleAPI:
    """
    A wrapper class for interacting with the Speckle API using the SpecklePy SDK.
    Supports token-based authentication for server-side operations.
    """
    def __init__(self, token: str = None, host: str = "https://app.speckle.systems"):
        """
        Initialize the Speckle API client with a specific token.
        
        Args:
            token (str): Speckle API token
            host (str): Speckle server URL
        """
        self.host = host
        self.client = SpeckleClient(host=host)
        
        if token:
            self.authenticate_with_token(token)
    
    def authenticate_with_token(self, token: str) -> None:
        """
        Authenticate the client using a token.
        
        Args:
            token (str): Speckle API token
        """
        try:
            speckle_token = Token(
                token=token,
                server_name=self.host
            )
            self.client.authenticate_with_token(speckle_token)
            logger.info(f"Successfully authenticated with Speckle at {self.host}")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise

    async def get_user_projects(self) -> List[Dict]:
        """
        Fetch all projects the user has access to via the Speckle API.
        
        Returns:
            List[Dict]: List of project data
        """
        try:
            projects = self.client.active_user.get_projects()
            return projects
        except Exception as e:
            logger.error(f"Error fetching user projects: {str(e)}")
            raise

    async def get_project_details(self, project_id: str) -> Dict:
        """
        Fetch detailed information about a specific project.
        
        Args:
            project_id (str): Project ID
            
        Returns:
            Dict: Project details
        """
        try:
            project = self.client.project.get(id=project_id)
            
            # Fetch additional information like models and collaborators
            if project:
                # Get models (streams) in this project
                models = self.client.project.get_models(project_id)
                project['models'] = models
                
                # Get collaborators 
                collaborators = self.client.project.get_collaborators(project_id)
                project['collaborators'] = collaborators
            
            return project
        except Exception as e:
            logger.error(f"Error fetching project details for {project_id}: {str(e)}")
            raise

    async def get_model_versions(self, model_id: str) -> List[Dict]:
        """
        Fetch versions for a specific model.
        
        Args:
            model_id (str): Model ID
            
        Returns:
            List[Dict]: List of versions
        """
        try:
            return self.client.model.get_versions(model_id=model_id)
        except Exception as e:
            logger.error(f"Error fetching versions for model {model_id}: {str(e)}")
            raise

    async def get_version_objects(self, version_id: str, limit: int = 100) -> Dict:
        """
        Fetch objects for a specific version with pagination support.
        
        Args:
            version_id (str): Version ID
            limit (int): Maximum number of objects to return
            
        Returns:
            Dict: Version objects
        """
        try:
            version = self.client.version.get(version_id=version_id)
            
            # Create a server transport for this specific stream
            stream_id = version.streamId
            transport = ServerTransport(self.client, stream_id)
            
            # Receive the objects with the transport
            obj = operations.receive(version.referencedObject, self.client, transport)
            
            return obj
        except Exception as e:
            logger.error(f"Error fetching objects for version {version_id}: {str(e)}")
            raise

    async def run_graphql_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """
        Run a custom GraphQL query against the Speckle API.
        
        Args:
            query (str): GraphQL query
            variables (Dict, optional): Variables for the query
            
        Returns:
            Dict: Query results
        """
        try:
            if not variables:
                variables = {}
                
            result = self.client.httpclient.query(query, variables)
            return result
        except Exception as e:
            logger.error(f"GraphQL query error: {str(e)}")
            raise
    
    async def create_comment(self, stream_id: str, object_id: str, message: str) -> Dict:
        """
        Create a comment on a specific object.
        
        Args:
            stream_id (str): Stream ID
            object_id (str): Object ID
            message (str): Comment message
            
        Returns:
            Dict: Created comment
        """
        try:
            return self.client.comment.create(
                stream_id=stream_id,
                object_id=object_id,
                message=message
            )
        except Exception as e:
            logger.error(f"Error creating comment: {str(e)}")
            raise
            
    async def search_objects(self, stream_id: str, query: str) -> List[Dict]:
        """
        Search for objects in a stream that match the query.
        
        Args:
            stream_id (str): Stream ID
            query (str): Search query
            
        Returns:
            List[Dict]: Search results
        """
        try:
            results = self.client.object.search(stream_id, query)
            return results
        except Exception as e:
            logger.error(f"Error searching objects: {str(e)}")
            raise

# Helper functions to create instances without class initialization
async def get_user_projects(token: str, host: str = "https://app.speckle.systems") -> List[Dict]:
    """
    Get all projects a user has access to.
    
    Args:
        token (str): Speckle API token
        host (str): Speckle server URL
        
    Returns:
        List[Dict]: User's projects
    """
    api = SpeckleAPI(token=token, host=host)
    return await api.get_user_projects()

async def get_project_details(token: str, project_id: str, host: str = "https://app.speckle.systems") -> Dict:
    """
    Get detailed information about a project.
    
    Args:
        token (str): Speckle API token
        project_id (str): Project ID
        host (str): Speckle server URL
        
    Returns:
        Dict: Project details
    """
    api = SpeckleAPI(token=token, host=host)
    return await api.get_project_details(project_id)