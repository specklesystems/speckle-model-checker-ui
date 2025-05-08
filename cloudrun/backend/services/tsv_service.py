import csv
from io import StringIO
from typing import Dict, List, Tuple


def generate_ruleset_tsv(ruleset: Dict, rules: List[Dict]) -> Tuple[str, str]:
    """Generate TSV content for a ruleset.

    Args:
        ruleset: Dictionary containing ruleset data
        rules: List of rule dictionaries

    Returns:
        Tuple of (tsv_content, filename)
    """
    # Generate TSV
    output = StringIO()
    writer = csv.writer(output, delimiter="\t")

    # Write header
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
        conditions = rule.get("conditions", [])

        # Skip empty rules
        if not conditions:
            continue

        # For each condition except the last one
        for i, condition in enumerate(conditions[:-1]):
            row = []

            # Only include rule number on first row
            if i == 0:
                row.append(str(rule_number))
            else:
                row.append("")

            row.append(condition.get("logic", ""))
            row.append(condition.get("propertyName", ""))
            row.append(condition.get("predicate", ""))
            row.append(condition.get("value", ""))
            row.append("")  # Empty severity
            row.append("")  # Empty message

            writer.writerow(row)

        # For the last condition, include severity and message
        if conditions:
            last_condition = conditions[-1]
            row = []

            # Only include rule number on first row if there was only one condition
            if len(conditions) == 1:
                row.append(str(rule_number))
            else:
                row.append("")

            row.append(last_condition.get("logic", ""))
            row.append(last_condition.get("propertyName", ""))
            row.append(last_condition.get("predicate", ""))
            row.append(last_condition.get("value", ""))
            row.append(rule.get("severity", "Error"))
            row.append(rule.get("message", ""))

            writer.writerow(row)

        rule_number += 1

    # Create filename
    filename = f"{ruleset.get('name', 'ruleset').replace(' ', '_').lower()}.tsv"

    return output.getvalue(), filename
