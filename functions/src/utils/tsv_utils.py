"""
Utility functions for TSV generation used across multiple modules.
"""

import csv
from io import StringIO


def generate_ruleset_tsv(ruleset, rules=None):
    """
    Generate TSV content for a ruleset with severity and message on the last row of each rule.

    Args:
        ruleset (dict): Ruleset document with ruleset metadata
        rules (list, optional): List of rule documents. If None, will use ruleset["rules"]

    Returns:
        tuple: (tsv_content, filename)
    """
    # Use provided rules or get from ruleset
    if rules is None:
        rules = ruleset.get("rules", [])

    # Generate TSV
    output = StringIO()
    writer = csv.writer(output, delimiter="\t")

    # Write header with "Rule Number" instead of "Rule #"
    writer.writerow(
        [
            "Rule Number",
            "Logic",
            "Property Name",
            "Predicate",
            "Value",
            "Report Severity",
            "Message",
        ]
    )

    # Write rules
    rule_number = 1
    for rule in rules:
        # Get all conditions for this rule
        conditions = rule.get("conditions", [])

        # Skip empty rules
        if not conditions:
            continue

        # For each condition except the last one
        for i, condition in enumerate(conditions[:-1]):
            row = []

            # Only include rule number on first row
            if i == 0:
                row.append(str(rule_number))  # Rule number
            else:
                row.append("")  # Empty rule number for middle conditions

            row.append(condition.get("logic", ""))  # Logic
            row.append(condition.get("propertyName", ""))  # Property Path
            row.append(condition.get("predicate", ""))  # Predicate
            row.append(condition.get("value", ""))  # Value
            row.append("")  # Empty severity for non-last conditions
            row.append("")  # Empty message for non-last conditions

            writer.writerow(row)

        # For the last condition, include severity and message
        if conditions:
            last_condition = conditions[-1]
            row = []

            # Only include rule number on first row if there was only one condition
            if len(conditions) == 1:
                row.append(str(rule_number))  # Rule number
            else:
                row.append(
                    ""
                )  # Empty rule number for last condition if not the only condition

            row.append(last_condition.get("logic", ""))  # Logic
            row.append(last_condition.get("propertyName", ""))  # Property Path
            row.append(last_condition.get("predicate", ""))  # Predicate
            row.append(last_condition.get("value", ""))  # Value
            row.append(rule.get("severity", "Error"))  # Severity on last row
            row.append(rule.get("message", ""))  # Message on last row

            writer.writerow(row)

        rule_number += 1

    # Create filename based on ruleset name
    filename = f"{ruleset.get('name', 'ruleset').replace(' ', '_').lower()}.tsv"

    return output.getvalue(), filename
