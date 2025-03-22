from firebase_admin import auth
from google.cloud import firestore
import datetime

# Verify challenge exists and hasn't been used
db = firestore.Client()


def get_rulesets_for_project(user_id, project_id):
    """
    Get all rulesets for a specific project.

    Args:
        user_id (str): User ID
        project_id (str): Project ID

    Returns:
        list: List of ruleset documents
    """

    rulesets = fetch_rulesets(db, user_id, project_id)

    return rulesets


import traceback


def fetch_rulesets(db, user_id, project_id):
    try:

        query = (
            db.collection("ruleSets")
            .where("userId", "==", user_id)
            .where("projectId", "==", project_id)
            .order_by("updatedAt", direction=firestore.Query.DESCENDING)
        )

        ruleset_docs = query.get()

        # Format results
        rulesets = []
        for doc in ruleset_docs:
            ruleset = doc.to_dict()
            ruleset["id"] = doc.id

            # Format timestamps
            if ruleset.get("updatedAt"):
                try:
                    ruleset["updated_at"] = ruleset["updatedAt"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                except Exception as e:
                    print(f"Timestamp formatting error for doc {doc.id}: {e}")
                    ruleset["updated_at"] = "Invalid timestamp"
            else:
                ruleset["updated_at"] = "Never"

            # Count rules
            ruleset["rule_count"] = len(ruleset.get("rules", []))

            rulesets.append(ruleset)

        return rulesets

    except Exception as e:
        print("An error occurred while fetching or formatting rulesets:")
        traceback.print_exc()
        return []


def create_ruleset(user_id, project_id, name, description=""):
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

    # Prepare ruleset document
    ruleset = {
        "name": name,
        "description": description,
        "userId": user_id,
        "projectId": project_id,
        "rules": [],
        "isShared": False,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    # Add to Firestore
    timestamp, ruleset_ref = db.collection("ruleSets").add(ruleset)

    # Get the created document
    ruleset_doc = ruleset_ref.get()
    result = ruleset_doc.to_dict()
    result["id"] = ruleset_doc.id

    # Format timestamps
    if result.get("updatedAt"):
        result["updated_at"] = result["updatedAt"].strftime("%Y-%m-%d %H:%M:%S")

    result["rule_count"] = 0

    return result


def safe_verify_id_token(id_token):
    try:
        return auth.verify_id_token(id_token)
    except Exception as e:
        if "Token used too early" in str(e):
            time.sleep(1)  # wait 1 second and retry
            return auth.verify_id_token(id_token)
        else:
            raise e


def get_ruleset(ruleset_id):
    """
    Get a ruleset by ID.

    Args:
        ruleset_id (str): Ruleset ID

    Returns:
        dict: Ruleset document with ID
    """

    # Get the document
    ruleset_doc = db.collection("ruleSets").document(ruleset_id).get()

    if not ruleset_doc.exists:
        return None

    # Format the result
    ruleset = ruleset_doc.to_dict()
    ruleset["id"] = ruleset_doc.id

    # Format timestamps
    if ruleset.get("updatedAt"):
        ruleset["updated_at"] = ruleset["updatedAt"].strftime("%Y-%m-%d %H:%M:%S")

    return ruleset


def update_ruleset(ruleset_id, data):
    """
    Update a ruleset.

    Args:
        ruleset_id (str): Ruleset ID
        data (dict): Fields to update

    Returns:
        bool: Success status
    """

    # Add updatedAt timestamp
    update_data = data.copy()
    update_data["updatedAt"] = firestore.SERVER_TIMESTAMP

    # Update document
    db.collection("ruleSets").document(ruleset_id).update(update_data)

    return True


def delete_ruleset(ruleset_id):
    """
    Delete a ruleset.

    Args:
        ruleset_id (str): Ruleset ID

    Returns:
        bool: Success status
    """

    # Delete document
    db.collection("ruleSets").document(ruleset_id).delete()

    return True


def toggle_ruleset_sharing(ruleset_id):
    """
    Toggle sharing status for a ruleset.

    Args:
        ruleset_id (str): Ruleset ID

    Returns:
        bool: New sharing status
    """

    # Get current status
    ruleset_doc = db.collection("ruleSets").document(ruleset_id).get()
    if not ruleset_doc.exists:
        return False

    ruleset = ruleset_doc.to_dict()
    is_shared = not ruleset.get("isShared", False)

    # Update sharing status
    update_data = {"isShared": is_shared, "updatedAt": firestore.SERVER_TIMESTAMP}

    # Add sharedAt timestamp if newly shared
    if is_shared and not ruleset.get("sharedAt"):
        update_data["sharedAt"] = firestore.SERVER_TIMESTAMP

    # Update document
    db.collection("ruleSets").document(ruleset_id).update(update_data)

    return is_shared


def get_shared_ruleset(ruleset_id):
    """
    Get a shared ruleset by ID, if it's shared.

    Args:
        ruleset_id (str): Ruleset ID

    Returns:
        dict: Ruleset document if shared, None otherwise
    """

    # Get the document
    ruleset_doc = db.collection("ruleSets").document(ruleset_id).get()

    if not ruleset_doc.exists:
        return None

    ruleset = ruleset_doc.to_dict()

    # Check if shared
    if not ruleset.get("isShared", False):
        return None

    # Format the result
    ruleset["id"] = ruleset_doc.id

    # Format timestamps
    if ruleset.get("updatedAt"):
        ruleset["updated_at"] = ruleset["updatedAt"].strftime("%Y-%m-%d %H:%M:%S")

    return ruleset


def get_rules_for_ruleset(ruleset_id):
    """
    Get all rules for a ruleset from the subcollection.

    Args:
        ruleset_id (str): Ruleset ID

    Returns:
        list: List of rule documents with IDs
    """

    rules_ref = (
        db.collection("ruleSets")
        .document(ruleset_id)
        .collection("rules")
        .order_by("order")
    )
    rules_docs = rules_ref.get()

    rules = []
    for doc in rules_docs:
        rule = doc.to_dict()
        rule["id"] = doc.id  # Add the document ID
        rules.append(rule)

    return rules


def create_rule(ruleset_id, user_id, rule_data):
    """
    Create a new rule in a ruleset.

    Args:
        ruleset_id (str): Ruleset ID
        user_id (str): User ID
        rule_data (dict): Rule data including message, severity, and conditions

    Returns:
        dict: Created rule with ID
    """

    # Get current rule count for ordering
    existing_rules = get_rules_for_ruleset(ruleset_id)

    # Prepare rule document
    new_rule = {
        "message": rule_data.get("message"),
        "severity": rule_data.get("severity"),
        "conditions": rule_data.get("conditions", []),
        "rulesetId": ruleset_id,
        "userId": user_id,
        "createdAt": firestore.SERVER_TIMESTAMP,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "order": len(existing_rules),  # Set order for sorting
    }

    # Add to rules subcollection
    timestamp, rule_ref = (
        db.collection("ruleSets").document(ruleset_id).collection("rules").add(new_rule)
    )

    # Get the created document
    try:
        rule_doc = rule_ref.get()
        result = rule_doc.to_dict()
        result["id"] = rule_doc.id
    except Exception as e:
        print("Error creating rule:", e)

    return result


def get_rule(ruleset_id, rule_id):
    """
    Get a rule by ID.

    Args:
        ruleset_id (str): Ruleset ID
        rule_id (str): Rule ID

    Returns:
        dict: Rule document with ID or None if not found
    """

    rule_doc = (
        db.collection("ruleSets")
        .document(ruleset_id)
        .collection("rules")
        .document(rule_id)
        .get()
    )

    if not rule_doc.exists:
        return None

    rule = rule_doc.to_dict()
    rule["id"] = rule_doc.id

    return rule


def update_single_rule(ruleset_id, rule_id, data):
    """
    Update a rule.

    Args:
        ruleset_id (str): Ruleset ID
        rule_id (str): Rule ID
        data (dict): Fields to update

    Returns:
        bool: Success status
    """

    # Add updatedAt timestamp
    update_data = data.copy()
    update_data["updatedAt"] = firestore.SERVER_TIMESTAMP

    # Update document
    db.collection("ruleSets").document(ruleset_id).collection("rules").document(
        rule_id
    ).update(update_data)

    return True


def delete_single_rule(ruleset_id, rule_id):
    """
    Delete a rule.

    Args:
        ruleset_id (str): Ruleset ID
        rule_id (str): Rule ID

    Returns:
        bool: Success status
    """

    # Delete document
    db.collection("ruleSets").document(ruleset_id).collection("rules").document(
        rule_id
    ).delete()

    # Optionally, reorder remaining rules
    reorder_rules(ruleset_id)

    return True


def reorder_rules(ruleset_id):
    """
    Reorder rules after deletion to maintain sequential order.

    Args:
        ruleset_id (str): Ruleset ID
    """

    # Get all rules sorted by current order
    rules_ref = (
        db.collection("ruleSets")
        .document(ruleset_id)
        .collection("rules")
        .order_by("order")
    )
    rules_docs = rules_ref.get()

    # Update order for each rule
    batch = db.batch()
    for i, doc in enumerate(rules_docs):
        rule_ref = (
            db.collection("ruleSets")
            .document(ruleset_id)
            .collection("rules")
            .document(doc.id)
        )
        batch.update(rule_ref, {"order": i})

    # Commit batch update
    batch.commit()
