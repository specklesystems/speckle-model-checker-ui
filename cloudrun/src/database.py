# cloudrun/src/database.py - Firestore Operations
from google.cloud import firestore


def get_rulesets_for_project(app, user_id, project_id):
    """Get all rulesets for a project"""
    query = (
        app.db.collection("ruleSets")
        .where("userId", "==", user_id)
        .where("projectId", "==", project_id)
        .order_by("updatedAt", direction=firestore.Query.DESCENDING)
    )

    ruleset_docs = query.get()

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
            except:
                ruleset["updated_at"] = "Invalid timestamp"
        else:
            ruleset["updated_at"] = "Never"

        rulesets.append(ruleset)

    return rulesets


def get_rules_for_ruleset(app, ruleset_id):
    """Get all rules for a ruleset"""
    rules_ref = (
        app.db.collection("ruleSets")
        .document(ruleset_id)
        .collection("rules")
        .order_by("order")
    )
    rules_docs = rules_ref.get()

    rules = []
    for doc in rules_docs:
        rule = doc.to_dict()
        rule["id"] = doc.id
        rules.append(rule)

    return rules


def get_user_token(app, user_id):
    """Get Speckle token for user"""
    user_token_doc = app.db.collection("userTokens").document(user_id).get()
    if not user_token_doc.exists:
        return None

    return user_token_doc.to_dict().get("speckleToken")


def create_ruleset(app, user_id, project_id, name, description=""):
    """Create a new ruleset"""
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

    timestamp, ruleset_ref = app.db.collection("ruleSets").add(ruleset)
    ruleset_doc = ruleset_ref.get()
    result = ruleset_doc.to_dict()
    result["id"] = ruleset_doc.id

    return result


def update_ruleset(app, ruleset_id, data):
    """Update a ruleset"""
    update_data = data.copy()
    update_data["updatedAt"] = firestore.SERVER_TIMESTAMP

    app.db.collection("ruleSets").document(ruleset_id).update(update_data)
    return True


def delete_ruleset(app, ruleset_id):
    """Delete a ruleset"""
    app.db.collection("ruleSets").document(ruleset_id).delete()
    return True


def toggle_ruleset_sharing(app, ruleset_id):
    """Toggle sharing status for a ruleset"""
    ruleset_doc = app.db.collection("ruleSets").document(ruleset_id).get()
    if not ruleset_doc.exists:
        return False

    ruleset = ruleset_doc.to_dict()
    is_shared = not ruleset.get("isShared", False)

    update_data = {
        "isShared": is_shared,
        "updatedAt": firestore.SERVER_TIMESTAMP,
    }

    if is_shared and not ruleset.get("sharedAt"):
        update_data["sharedAt"] = firestore.SERVER_TIMESTAMP

    app.db.collection("ruleSets").document(ruleset_id).update(update_data)
    return is_shared
