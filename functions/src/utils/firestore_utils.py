from firebase_admin import firestore
import datetime

async def get_rulesets_for_project(user_id, project_id):
    """
    Get all rulesets for a specific project.
    
    Args:
        user_id (str): User ID
        project_id (str): Project ID
        
    Returns:
        list: List of ruleset documents
    """
    db = firestore.client()
    
    # Query Firestore for rulesets matching both user and project
    query = db.collection('ruleSets').where(
        filter=firestore.and_filter([
            firestore.field_filter('userId', '==', user_id),
            firestore.field_filter('projectId', '==', project_id)
        ])
    ).order_by('updatedAt', direction=firestore.Query.DESCENDING)
    
    # Execute query
    ruleset_docs = query.get()
    
    # Format results
    rulesets = []
    for doc in ruleset_docs:
        ruleset = doc.to_dict()
        ruleset['id'] = doc.id
        
        # Format timestamps
        if ruleset.get('updatedAt'):
            ruleset['updated_at'] = ruleset['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
        else:
            ruleset['updated_at'] = 'Never'
        
        # Count rules
        ruleset['rule_count'] = len(ruleset.get('rules', []))
        
        rulesets.append(ruleset)
    
    return rulesets

async def create_ruleset(user_id, project_id, name, description=''):
    """
    Create a new ruleset.
    
    Args:
        user_id (str): User ID
        project_id (str): Project ID
        name (str): Ruleset name
        description (str, optional): Ruleset description
        
    Returns:
        dict: Created ruleset with ID
    """
    db = firestore.client()
    
    # Prepare ruleset document
    ruleset = {
        'name': name,
        'description': description,
        'userId': user_id,
        'projectId': project_id,
        'rules': [],
        'isShared': False,
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP
    }
    
    # Add to Firestore
    ruleset_ref = db.collection('ruleSets').add(ruleset)
    
    # Get the created document
    ruleset_doc = ruleset_ref.get()
    result = ruleset_doc.to_dict()
    result['id'] = ruleset_doc.id
    
    # Format timestamps
    if result.get('updatedAt'):
        result['updated_at'] = result['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
    
    result['rule_count'] = 0
    
    return result

async def get_ruleset(ruleset_id):
    """
    Get a ruleset by ID.
    
    Args:
        ruleset_id (str): Ruleset ID
        
    Returns:
        dict: Ruleset document with ID
    """
    db = firestore.client()
    
    # Get the document
    ruleset_doc = db.collection('ruleSets').document(ruleset_id).get()
    
    if not ruleset_doc.exists:
        return None
    
    # Format the result
    ruleset = ruleset_doc.to_dict()
    ruleset['id'] = ruleset_doc.id
    
    # Format timestamps
    if ruleset.get('updatedAt'):
        ruleset['updated_at'] = ruleset['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
    
    return ruleset

async def update_ruleset(ruleset_id, data):
    """
    Update a ruleset.
    
    Args:
        ruleset_id (str): Ruleset ID
        data (dict): Fields to update
        
    Returns:
        bool: Success status
    """
    db = firestore.client()
    
    # Add updatedAt timestamp
    update_data = data.copy()
    update_data['updatedAt'] = firestore.SERVER_TIMESTAMP
    
    # Update document
    db.collection('ruleSets').document(ruleset_id).update(update_data)
    
    return True

async def delete_ruleset(ruleset_id):
    """
    Delete a ruleset.
    
    Args:
        ruleset_id (str): Ruleset ID
        
    Returns:
        bool: Success status
    """
    db = firestore.client()
    
    # Delete document
    db.collection('ruleSets').document(ruleset_id).delete()
    
    return True

async def toggle_ruleset_sharing(ruleset_id):
    """
    Toggle sharing status for a ruleset.
    
    Args:
        ruleset_id (str): Ruleset ID
        
    Returns:
        bool: New sharing status
    """
    db = firestore.client()
    
    # Get current status
    ruleset_doc = db.collection('ruleSets').document(ruleset_id).get()
    if not ruleset_doc.exists:
        return False
    
    ruleset = ruleset_doc.to_dict()
    is_shared = not ruleset.get('isShared', False)
    
    # Update sharing status
    update_data = {
        'isShared': is_shared,
        'updatedAt': firestore.SERVER_TIMESTAMP
    }
    
    # Add sharedAt timestamp if newly shared
    if is_shared and not ruleset.get('sharedAt'):
        update_data['sharedAt'] = firestore.SERVER_TIMESTAMP
    
    # Update document
    db.collection('ruleSets').document(ruleset_id).update(update_data)
    
    return is_shared

async def get_shared_ruleset(ruleset_id):
    """
    Get a shared ruleset by ID, if it's shared.
    
    Args:
        ruleset_id (str): Ruleset ID
        
    Returns:
        dict: Ruleset document if shared, None otherwise
    """
    db = firestore.client()
    
    # Get the document
    ruleset_doc = db.collection('ruleSets').document(ruleset_id).get()
    
    if not ruleset_doc.exists:
        return None
    
    ruleset = ruleset_doc.to_dict()
    
    # Check if shared
    if not ruleset.get('isShared', False):
        return None
    
    # Format the result
    ruleset['id'] = ruleset_doc.id
    
    # Format timestamps
    if ruleset.get('updatedAt'):
        ruleset['updated_at'] = ruleset['updatedAt'].strftime('%Y-%m-%d %H:%M:%S')
    
    return ruleset