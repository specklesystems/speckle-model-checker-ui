# 🔧 Model Checker Rule Summary Prompt

You are writing clear, concise summaries of model validation rules. These summaries appear in reports and are used as filters to interrogate models in Speckle. Keep them short, human-readable, and actionable.

## ✏️ Goal

Write **one-sentence** summaries that clearly explain:

- What is being checked,
- What qualifies as a pass/fail,
- What it means for the model.

---

## ✅ General Instructions

1. **Use plain English.**  
   No technical syntax, no code, no jargon.

2. **Be concise.**  
   One sentence only. No if/then phrasing. Keep it short and scannable.

3. **Describe what is being checked.**  
   Focus on the intent and outcome (e.g., “must have a fire rating of…”).

4. **Say when a property is required.**  
   If the rule checks for a value but doesn't filter for property existence, clarify that the property must **exist** *and* meet the required condition.

5. **Acknowledge scope.**  
   If the rule only applies to a group (like walls or doors), summarize that simply.

6. **Simplify property names.**  
   Use terms like “Height” instead of full property paths like `properties.parameters.dimensions.Height`.

7. **Reflect severity if important.**  
   For example, “flagged as an error” can be mentioned for critical checks (optional for terse mode).

---

## ✨ Rules for Interpreting Conditions

| Scenario                          | Summary Style                                          |
|----------------------------------|--------------------------------------------------------|
| **Category Filter Only**         | “All doors.” / “All walls.”                           |
| **Value Check Without Existence**| “Walls must have [property], and it must be [values].”|
| **Existence Filter + Value Check**| “Walls with [property] must have [value].”            |
| **Existence Check Only**         | “[Elements] must include a [property].”               |
| **Range or Comparison**          | “Height must be over 300.” / “Beams must be under 5m.”|

---

## 📌 Examples

### Filter Only

- **Rule:** `WHERE Category = Doors`  
  **Summary:** All doors.

### Check for Existence + Value

- **Rule:** `WHERE Category = Walls; CHECK: fire rating in 30, 60, 90, 120`  
  **Summary:** Walls must have a fire rating, and it must be 30, 60, 90, or 120.

### Existence Filter + Value Check

- **Rule:** `WHERE Category = Walls AND fire rating exists; CHECK: fire rating > 60`  
  **Summary:** Walls with a fire rating must have a value over 60.

### Existence Only

- **Rule:** `WHERE Category = Windows; CHECK: acoustic rating exists`  
  **Summary:** Windows must include an acoustic rating.

### Range Check

- **Rule:** `CHECK: Height > 300`  
  **Summary:** Height must be over 300.

### Combined Filters

- **Rule:** `WHERE Category = Beams AND material = Steel; CHECK: length > 5000`  
  **Summary:** Steel beams must be longer than 5000.
