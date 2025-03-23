import csv
import io

from firebase_functions import https_fn

from ..utils.firestore_utils import get_ruleset, get_shared_ruleset


def export_ruleset_as_tsv(request, ruleset_id):
    """Export a ruleset as a TSV file."""
    try:
        # Get user info from request
        user_id = request.user_id

        # Get the ruleset
        ruleset = get_ruleset(ruleset_id)

        # If not found as a private ruleset, try as a shared ruleset
        if not ruleset:
            ruleset = get_shared_ruleset(ruleset_id)

        if not ruleset:
            return https_fn.Response(
                "Ruleset not found", mimetype="text/plain", status=404
            )

        # Verify ownership if not a shared ruleset
        if not ruleset.get("isShared", False) and ruleset.get("userId") != user_id:
            return https_fn.Response(
                "You don't have permission to export this ruleset",
                mimetype="text/plain",
                status=403,
            )

        # Generate TSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter="\t")

        # Write header
        writer.writerow(
            [
                "Rule #",
                "Logic",
                "Property Path",
                "Predicate",
                "Value",
                "Severity",
                "Message",
            ]
        )

        # Write rules
        rule_number = 1
        for rule in ruleset.get("rules", []):
            # First condition row includes the rule number, severity, and message
            first_condition = True

            for condition in rule.get("conditions", []):
                row = []

                if first_condition:
                    row.append(str(rule_number))  # Rule number
                    first_condition = False
                else:
                    row.append("")  # Empty rule number for additional conditions

                row.append(condition.get("logic", ""))  # Logic
                row.append(condition.get("propertyName", ""))  # Property Path
                row.append(condition.get("predicate", ""))  # Predicate
                row.append(condition.get("value", ""))  # Value

                if first_condition:
                    row.append(rule.get("severity", "Error"))  # Severity
                    row.append(rule.get("message", ""))  # Message
                else:
                    row.append("")  # Empty severity for additional conditions
                    row.append("")  # Empty message for additional conditions

                writer.writerow(row)

            rule_number += 1

        # Set headers for file download
        filename = f"{ruleset.get('name', 'ruleset').replace(' ', '_').lower()}.tsv"

        return https_fn.Response(
            output.getvalue(),
            mimetype="text/tab-separated-values",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        return https_fn.Response(
            f"Error exporting ruleset: {str(e)}",
            mimetype="text/plain",
            status=500,
        )


# Create Firebase Function
def export_ruleset_handler(request):
    ruleset_id = request.args.get("ruleset_id")  # Extract from query params
    return export_ruleset_as_tsv(request, ruleset_id)


export_ruleset_fn = https_fn.on_request()(export_ruleset_handler)
