# Model Checker

Model Checker is an Automate function that validates Speckle objects against configurable rules. This approach provides a flexible way to implement quality checks and maintain consistent standards across projects.

## Overview

The Model Checker allows you to:

- Define validation rules for your objects
- Configure severity levels for issues
- Check properties across different types of objects
- Generate reports of validation results
- Apply consistent standards across projects

## Getting Started

### 1. Access the Model Checker Application

1. Go to the [Model Checker Application](https://model-checker.speckle.systems)
2. Sign in with your Speckle account
3. Create and manage your validation rules through the intuitive web interface

### 2. Create an Automation

1. Go to your workspace project in [Speckle](https://app.speckle.systems/)
2. Create a new Automation
3. Select the Model Checker function
4. Configure the function:
   - Set minimum severity level to report
   - Configure other options as needed
5. Save and run your automation

## Rule Definition Format

Rules are defined with the following components:

| Logic | Property Name | Predicate    | Value     | Message              | Report Severity |
| ----- | ------------- | ------------ | --------- | -------------------- | --------------- |
| WHERE | category      | matches      | Walls     | Wall thickness check | ERROR           |
| CHECK | Width         | greater than | 200       |                      |                 |
| WHERE | category      | matches      | Columns   | Column height check  | WARNING         |
| AND   | height        | in range     | 2500,4000 |                      |                 |

### Component Explanation

- **Logic**: Defines how conditions are combined (WHERE, AND, CHECK)
- **Property Name**: The object property or parameter to check
- **Predicate**: Comparison operation (equals, greater than, etc.)
- **Value**: Reference value for comparison
- **Message**: Description shown in validation results
- **Report Severity**: ERROR, WARNING, or INFO

### Supported Predicates

| Predicate        | Description                 | Example                               |
| ---------------- | --------------------------- | ------------------------------------- |
| exists           | Checks if a property exists | `height` exists                       |
| equal to         | Exact value match           | `width` equal to `300`                |
| not equal to     | Value doesn't match         | `material` not equal to `Concrete`    |
| greater than     | Value exceeds threshold     | `height` greater than `3000`          |
| less than        | Value below threshold       | `thickness` less than `50`            |
| in range         | Value within bounds         | `elevation` in range `0,10000`        |
| in list          | Value in allowed set        | `type` in list `W1,W2,W3`             |
| contains         | Property contains substring | `name` contains `Beam`                |
| does not contain | Property doesn't contain    | `name` does not contain `temp`        |
| is true          | Boolean property is true    | `is_structural` is true               |
| is false         | Boolean property is false   | `is_placeholder` is false             |
| is like          | Loose text matching         | `name` is like `Wall` matches `Walls` |

## Rule Logic

- **WHERE**: Filters objects to check (like SELECT WHERE in SQL)
- **AND**: Additional filter conditions
- **CHECK**: Final check condition (optional, defaults to last AND)

Objects pass a rule when they match all conditions. Objects that match WHERE/AND filters but fail the CHECK condition are reported as issues.

## Working with Object Properties

The Model Checker understands properties in Speckle objects regardless of schema:

- Direct properties: `category`, `name`, `id`
- Nested properties: `parameters.WIDTH.value`
- Revit parameters: Use parameter names like `Mark`, `Width`, `Assembly Code`

## Example Rules

### Wall Thickness Check

```
Rule: WHERE category equals "Walls" AND width less than "200"
Message: "Walls must have width of at least 200."
Severity: ERROR
```

### Door Naming Convention

```
Rule: WHERE category equals "Doors" AND name is not like "^D\d{3}$"
Message: "All doors must have a name that follows the format "D" followed by three digits."
Severity: WARNING
```

### Structural Column Height Range

```
Rule: WHERE category equals "Columns" AND is_structural is true AND height not in range "2400,4000"
Message: "Structural columns must have a height between 2400 and 4000."
Severity: ERROR
```

## Support

For issues or questions, please let us know on the [Speckle Community Forum](https://speckle.community/).

### Alternative: TSV File Format

While the Model Checker Application is the recommended way to create and manage rules, you can also create compatible TSV (Tab-Separated Values) files manually. This can be useful for:

- Programmatically generating rules
- Version controlling rules in a text format
- Integrating with existing workflows
- Creating rules in bulk

The TSV file should follow the same structure as shown in the table above, with columns separated by tabs. The file will then need to be hosted somewhere and served with MIME-type of `text/tab-separated-values` and the URL used in the automation configuration.
