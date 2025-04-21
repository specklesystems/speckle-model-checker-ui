"""
Utility functions for managing predicate formats between UI, storage and automation.
"""

# Define the canonical predicate values matching the automation function
CANONICAL_PREDICATES = [
    "exists",
    "greater than",
    "less than",
    "in range",
    "in list",
    "equal to",
    "not equal to",
    "is true",
    "is false",
    "is like",
    "identical to",
    "contains",
    "does not contain",
]

# Map from storage formats (like "==") to canonical formats (like "equal to")
STORAGE_TO_CANONICAL = {
    "==": "equal to",
    "!=": "not equal to",
    ">": "greater than",
    "<": "less than",
    "range": "in range",
    "in": "in list",
    "true": "is true",
    "false": "is false",
    "like": "is like",
    "===": "identical to",
    "contains": "contains",
    "!contains": "does not contain",
    "exists": "exists",
}

# Reverse mapping (canonical to storage)
CANONICAL_TO_STORAGE = {v: k for k, v in STORAGE_TO_CANONICAL.items()}


def get_canonical_predicate(stored_predicate):
    """
    Convert a stored predicate format to the canonical format used by automation.

    Args:
        stored_predicate (str): The predicate as stored in Firestore

    Returns:
        str: The canonical predicate format used by automation
    """
    if not stored_predicate:
        print(f"WARNING: Empty predicate found, defaulting to 'exists'")
        return "exists"

    # If the stored predicate is already in canonical form, return it
    if stored_predicate in CANONICAL_PREDICATES:
        return stored_predicate

    # Otherwise, try to map it from storage format to canonical format
    canonical = STORAGE_TO_CANONICAL.get(stored_predicate)

    if canonical:
        print(f"Mapped predicate from '{stored_predicate}' to '{canonical}'")
        return canonical

    # If we can't map it directly, try case-insensitive matching
    for pred in CANONICAL_PREDICATES:
        if stored_predicate.lower() == pred.lower():
            print(f"Case-insensitive match: '{stored_predicate}' → '{pred}'")
            return pred

    # If all else fails, log and return the original
    print(f"WARNING: Unknown predicate format '{stored_predicate}', leaving as-is")
    return stored_predicate


def get_storage_predicate(canonical_predicate):
    """
    Convert a canonical predicate to storage format.

    Args:
        canonical_predicate (str): The canonical predicate from UI

    Returns:
        str: The predicate in storage format
    """
    # Return the canonical format directly - we'll now store in canonical format
    return canonical_predicate
