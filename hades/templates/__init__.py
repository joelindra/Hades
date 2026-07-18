"""Template management module for HADES"""

from .manager import (
    TemplateManager,
    get_template_path,
    list_templates,
    read_template,
    create_template,
    update_template,
    delete_template,
)

__all__ = [
    "TemplateManager",
    "get_template_path",
    "list_templates",
    "read_template",
    "create_template",
    "update_template",
    "delete_template",
]

