# cloudrun/src/utils.py - Utility Functions
from jinja2 import Environment, FileSystemLoader

# Create template loader
template_loader = FileSystemLoader("templates")
template_env = Environment(loader=template_loader, autoescape=True)


def render_template(template_name, **context):
    """Render a template file"""
    try:
        template = template_env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        return f"Error rendering template {template_name}: {str(e)}"


def get_location(request):
    """Get the application base URL"""
    if request.host:
        protocol = "https" if request.is_secure else "http"
        return f"{protocol}://{request.host}"
    return "https://speckle-model-checker.web.app"
