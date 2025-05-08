import uuid
from typing import List
from firebase_admin import firestore
from models import Ruleset, RulesetCreate, Rule, RuleCreate, RuleUpdate


class RulesetService:
    def __init__(self):
        self.db = firestore.client()
        self.rulesets_collection = self.db.collection("rulesets")

    async def create_ruleset(self, ruleset: RulesetCreate) -> Ruleset:
        """Create a new ruleset in Firebase."""
        # Generate a new ID
        ruleset_id = str(uuid.uuid4())

        # Create the ruleset document
        new_ruleset = Ruleset(
            id=ruleset_id,
            name=ruleset.name,
            description=ruleset.description,
            rules=[],  # Start with no rules
        )

        # Save to Firebase
        self.rulesets_collection.document(ruleset_id).set(new_ruleset.dict())

        return new_ruleset

    async def get_ruleset(self, ruleset_id: str) -> Ruleset:
        """Get a ruleset from Firebase."""
        doc = self.rulesets_collection.document(ruleset_id).get()
        if not doc.exists:
            raise ValueError(f"Ruleset {ruleset_id} not found")
        return Ruleset(**doc.to_dict())

    async def save_ruleset(self, ruleset: Ruleset) -> None:
        """Save a ruleset to Firebase."""
        self.rulesets_collection.document(ruleset.id).set(ruleset.dict())

    async def create_rule(self, ruleset_id: str, rule: RuleCreate) -> Rule:
        """Create a new rule in a ruleset."""
        ruleset = await self.get_ruleset(ruleset_id)
        new_rule = Rule(
            id=str(uuid.uuid4()),
            severity=rule.severity,
            message=rule.message,
            conditions=rule.conditions,
        )
        ruleset.rules.append(new_rule)
        await self.save_ruleset(ruleset)
        return new_rule

    async def update_rule(
        self, ruleset_id: str, rule_id: str, rule: RuleUpdate
    ) -> Rule:
        """Update an existing rule in a ruleset."""
        ruleset = await self.get_ruleset(ruleset_id)
        for i, r in enumerate(ruleset.rules):
            if r.id == rule_id:
                updated_rule = Rule(
                    id=rule_id,
                    severity=rule.severity,
                    message=rule.message,
                    conditions=rule.conditions,
                )
                ruleset.rules[i] = updated_rule
                await self.save_ruleset(ruleset)
                return updated_rule
        raise ValueError(f"Rule {rule_id} not found in ruleset {ruleset_id}")

    async def delete_rule(self, ruleset_id: str, rule_id: str) -> None:
        """Delete a rule from a ruleset."""
        ruleset = await self.get_ruleset(ruleset_id)
        ruleset.rules = [r for r in ruleset.rules if r.id != rule_id]
        await self.save_ruleset(ruleset)
