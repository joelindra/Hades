"""Template management for HADES scan instructions"""

import os
from pathlib import Path
from typing import List, Optional, Dict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def get_template_dir() -> Path:
    """Get the templates directory path"""
    script_dir = Path(__file__).parent.parent.parent.absolute()
    template_dir = script_dir / "templates"
    template_dir.mkdir(exist_ok=True)
    return template_dir


def get_template_path(template_name: str) -> Path:
    """Get the full path to a template file"""
    template_dir = get_template_dir()
    
    if " " in template_name:
        raise ValueError("Template name cannot contain spaces. Use underscores (_) or hyphens (-) instead.")
        
    # Sanitize template name to prevent path traversal
    safe_name = "".join(c for c in template_name if c.isalnum() or c in ("-", "_", "."))
    
    if not safe_name or safe_name != template_name:
        raise ValueError(f"Invalid template name: {template_name}. Only alphanumeric, hyphens, underscores and dots are allowed.")
    return template_dir / f"{safe_name}.txt"


def list_templates() -> List[str]:
    """List all available templates"""
    template_dir = get_template_dir()
    templates = []
    for file in template_dir.glob("*.txt"):
        templates.append(file.stem)
    return sorted(templates)


def read_template(template_name: str) -> Optional[str]:
    """
    Read a template file.
    
    Args:
        template_name: Name of the template (without .txt extension)
        
    Returns:
        Template content as string, or None if not found
    """
    try:
        template_path = get_template_path(template_name)
        if not template_path.exists():
            return None
        
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except Exception as e:
        console.print(f"[red]Error reading template: {e}[/red]")
        return None


def create_template(template_name: str, content: str) -> bool:
    """
    Create a new template.
    
    Args:
        template_name: Name of the template
        content: Template content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        template_path = get_template_path(template_name)
        if template_path.exists():
            console.print(f"[yellow]Template '{template_name}' already exists. Use update instead.[/yellow]")
            return False
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        console.print(f"[green]✓ Template '{template_name}' created successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error creating template: {e}[/red]")
        return False


def update_template(template_name: str, content: str) -> bool:
    """
    Update an existing template.
    
    Args:
        template_name: Name of the template
        content: New template content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        template_path = get_template_path(template_name)
        if not template_path.exists():
            console.print(f"[yellow]Template '{template_name}' does not exist. Use create instead.[/yellow]")
            return False
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        console.print(f"[green]✓ Template '{template_name}' updated successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error updating template: {e}[/red]")
        return False


def delete_template(template_name: str) -> bool:
    """
    Delete a template.
    
    Args:
        template_name: Name of the template
        
    Returns:
        True if successful, False otherwise
    """
    try:
        template_path = get_template_path(template_name)
        if not template_path.exists():
            console.print(f"[yellow]Template '{template_name}' does not exist.[/yellow]")
            return False
        
        template_path.unlink()
        console.print(f"[green]✓ Template '{template_name}' deleted successfully[/green]")
        return True
    except Exception as e:
        console.print(f"[red]Error deleting template: {e}[/red]")
        return False


class TemplateManager:
    """Interactive template manager with CRUD operations"""
    
    def __init__(self):
        self.template_dir = get_template_dir()
    
    def list_all(self) -> None:
        """Display all templates in a table"""
        templates = list_templates()
        
        if not templates:
            console.print("[yellow]No templates found. Create one using 'python main.py --templates create'[/yellow]")
            return
        
        table = Table(
            title="[bold cyan]Available Templates[/bold cyan]",
            show_header=True,
            header_style="bold bright_cyan",
            border_style="cyan",
            box=box.ROUNDED
        )
        table.add_column("Template Name", style="bold green", width=30)
        table.add_column("Size", style="dim", width=15)
        table.add_column("Preview", style="dim", width=50)
        
        for template_name in templates:
            content = read_template(template_name)
            if content:
                size = len(content)
                preview = content[:47] + "..." if len(content) > 50 else content
                table.add_row(template_name, f"{size} chars", preview)
            else:
                table.add_row(template_name, "Error", "Could not read")
        
        console.print(table)
    
    def create_interactive(self) -> None:
        """Interactive template creation"""
        from rich.prompt import Prompt
        
        console.print("[bold cyan]Create New Template[/bold cyan]\n")
        
        template_name = Prompt.ask("[bold yellow]Template name[/bold yellow]")
        if not template_name:
            console.print("[red]Template name cannot be empty[/red]")
            return
        
        # Check if template already exists
        if get_template_path(template_name).exists():
            from rich.prompt import Confirm
            if not Confirm.ask(f"[yellow]Template '{template_name}' already exists. Overwrite?[/yellow]"):
                return
        
        console.print("\n[dim]Enter template content (instruction).[/dim]")
        console.print("[dim]You can enter multiple lines. Press Enter twice (empty line) to finish, or Ctrl+D/Ctrl+Z to finish:[/dim]\n")
        
        lines = []
        empty_count = 0
        try:
            while True:
                line = input()
                if line.strip() == "":
                    empty_count += 1
                    if empty_count >= 2:  # Two consecutive empty lines = finish
                        break
                else:
                    empty_count = 0
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        
        content = "\n".join(lines).strip()
        
        if not content:
            console.print("[red]Template content cannot be empty[/red]")
            return
        
        if create_template(template_name, content) or update_template(template_name, content):
            console.print(f"\n[green]Template '{template_name}' saved![/green]")
            console.print(f"[dim]Use it with: python main.py --target <url> --templates {template_name}[/dim]")
    
    def edit_interactive(self, template_name: Optional[str] = None) -> None:
        """Interactive template editing"""
        from rich.prompt import Prompt
        
        if not template_name:
            templates = list_templates()
            if not templates:
                console.print("[yellow]No templates available to edit[/yellow]")
                return
            
            console.print("\n[bold cyan]Select Template to Edit[/bold cyan]\n")
            for i, name in enumerate(templates, 1):
                console.print(f"  {i}. {name}")
            
            choice = Prompt.ask("\n[bold yellow]Enter template number or name[/bold yellow]")
            
            # Try to parse as number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(templates):
                    template_name = templates[idx]
                else:
                    console.print("[red]Invalid selection[/red]")
                    return
            except ValueError:
                # Treat as name
                template_name = choice
        
        content = read_template(template_name)
        if content is None:
            console.print(f"[red]Template '{template_name}' not found[/red]")
            return
        
        console.print(f"\n[bold cyan]Editing Template: {template_name}[/bold cyan]")
        console.print("[dim]Current content:[/dim]\n")
        console.print(Panel(content, border_style="cyan", box=box.ROUNDED))
        console.print("\n[dim]Enter new content.[/dim]")
        console.print("[dim]You can enter multiple lines. Press Enter twice (empty line) to finish, or Ctrl+D/Ctrl+Z to finish:[/dim]\n")
        
        lines = []
        empty_count = 0
        try:
            while True:
                line = input()
                if line.strip() == "":
                    empty_count += 1
                    if empty_count >= 2:  # Two consecutive empty lines = finish
                        break
                else:
                    empty_count = 0
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        
        new_content = "\n".join(lines).strip()
        
        if not new_content:
            from rich.prompt import Confirm
            if not Confirm.ask("[yellow]Content is empty. Delete template instead?[/yellow]"):
                return
            delete_template(template_name)
        else:
            update_template(template_name, new_content)
            console.print(f"\n[green]Template '{template_name}' updated![/green]")
    
    def delete_interactive(self, template_name: Optional[str] = None) -> None:
        """Interactive template deletion"""
        from rich.prompt import Prompt, Confirm
        
        if not template_name:
            templates = list_templates()
            if not templates:
                console.print("[yellow]No templates available to delete[/yellow]")
                return
            
            console.print("\n[bold cyan]Select Template to Delete[/bold cyan]\n")
            for i, name in enumerate(templates, 1):
                console.print(f"  {i}. {name}")
            
            choice = Prompt.ask("\n[bold yellow]Enter template number or name[/bold yellow]")
            
            # Try to parse as number
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(templates):
                    template_name = templates[idx]
                else:
                    console.print("[red]Invalid selection[/red]")
                    return
            except ValueError:
                # Treat as name
                template_name = choice
        
        if not get_template_path(template_name).exists():
            console.print(f"[red]Template '{template_name}' not found[/red]")
            return
        
        content = read_template(template_name)
        if content:
            console.print("\n[bold yellow]Template Content:[/bold yellow]")
            console.print(Panel(content[:200] + ("..." if len(content) > 200 else ""), border_style="yellow", box=box.ROUNDED))
        
        if Confirm.ask(f"\n[bold red]Are you sure you want to delete template '{template_name}'?[/bold red]"):
            delete_template(template_name)
        else:
            console.print("[yellow]Deletion cancelled[/yellow]")
    
    def show(self, template_name: str) -> None:
        """Display a template"""
        content = read_template(template_name)
        if content is None:
            console.print(f"[red]Template '{template_name}' not found[/red]")
            return
        
        console.print(f"\n[bold cyan]Template: {template_name}[/bold cyan]")
        console.print(Panel(content, border_style="cyan", box=box.ROUNDED, title="[bold]Content[/bold]"))
        console.print(f"\n[dim]Use with: python main.py --target <url> --templates {template_name}[/dim]")

