import datetime
import os

from jinja2 import Environment, FileSystemLoader

# Determine the template directories
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
main_template_dir = os.path.join(current_dir, "templates")

# Create template loader that checks multiple template directories
template_dirs = [main_template_dir]

# Add module-specific template directories
modules = ["auth", "projects", "rulesets", "rules"]
for module in modules:
    module_template_dir = os.path.join(current_dir, module, "templates")
    if os.path.exists(module_template_dir):
        template_dirs.append(module_template_dir)

# Create Jinja environment with file system loader
env = Environment(loader=FileSystemLoader(template_dirs), autoescape=True)


# Add custom filters
def format_date(value, format="%Y-%m-%d"):
    """Format a date."""
    if isinstance(value, str):
        try:
            value = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return value
    if value is None:
        return ""
    return value.strftime(format)


env.filters["date"] = format_date


def render_template(template_name, **context):
    """
    Render a template from file.

    Args:
        template_name: The template file name
        **context: Template context variables

    Returns:
        str: Rendered template
    """
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        # Return error message if template fails to load
        return f"Error rendering template {template_name}: {str(e)}"
