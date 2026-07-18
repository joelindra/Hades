import sys
import os
import argparse
import subprocess
import traceback
import re
import logging
import warnings
import shutil
import json
from pathlib import Path

# Silence noisy 3rd party warnings and logs
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("paramiko").setLevel(logging.ERROR)
logging.getLogger("numexpr").setLevel(logging.ERROR)

from typing import Optional, Dict, List, Any, cast

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

from hades.config_loader import get_hades_version
from hades.web.database import flush_database

# ============================================================================
# Constants
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
VERSION = "Pro-1.0.0"
AUTHOR = "Joel Indra - Anonre"

# ============================================================================
# Rich Library Import
# ============================================================================

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.columns import Columns
    from rich.align import Align
    from rich.prompt import Prompt, Confirm
    from rich import box
except ImportError:
    print("Error: rich library is required. Install with: pip install rich --break-system-packages")
    sys.exit(1)

console = Console()

# ============================================================================
# API Key Configuration
# ============================================================================

# AI Provider configurations
AI_PROVIDERS: Dict[str, Dict[str, str]] = {}

def init_providers():
    global AI_PROVIDERS
    providers_file = SCRIPT_DIR / "config" / "providers.json"

    # If config/providers.json doesn't exist, create it with default providers
    if not providers_file.exists():
        try:
            providers_file.parent.mkdir(exist_ok=True, parents=True)
            default_providers = {
                "1": {
                    "name": "Gemini 2.5 Pro",
                    "model": "gemini/gemini-2.5-pro",
                    "env_var": "GOOGLE_API_KEY",
                    "api_key_url": "https://aistudio.google.com/apikey",
                    "description": "Best for security analysis (Recommended)",
                    "icon": "🤖"
                },
                "2": {
                    "name": "Gemini Flash 2.5",
                    "model": "gemini/gemini-2.5-flash",
                    "env_var": "GOOGLE_API_KEY",
                    "api_key_url": "https://aistudio.google.com/apikey",
                    "description": "Fast and cost-effective",
                    "icon": "⚡"
                },
                "3": {
                    "name": "Anthropic Claude",
                    "model": "anthropic/claude-3-5-sonnet",
                    "env_var": "ANTHROPIC_API_KEY",
                    "api_key_url": "https://console.anthropic.com/",
                    "description": "Advanced reasoning capabilities",
                    "icon": "🧠"
                },
                "4": {
                    "name": "Claude 3.5 Haiku",
                    "model": "anthropic/claude-3-5-haiku",
                    "env_var": "ANTHROPIC_API_KEY",
                    "api_key_url": "https://console.anthropic.com/",
                    "description": "Fast and affordable Claude model",
                    "icon": "🚀"
                },
                "5": {
                    "name": "OpenAI GPT-4o",
                    "model": "openai/gpt-4o",
                    "env_var": "OPENAI_API_KEY",
                    "api_key_url": "https://platform.openai.com/api-keys",
                    "description": "Latest GPT-4 optimized model",
                    "icon": "✨"
                },
                "6": {
                    "name": "OpenAI GPT-4 Turbo",
                    "model": "openai/gpt-4-turbo",
                    "env_var": "OPENAI_API_KEY",
                    "api_key_url": "https://platform.openai.com/api-keys",
                    "description": "High-quality responses, premium pricing",
                    "icon": "💬"
                },
                "7": {
                    "name": "Groq Llama 3.3 70B",
                    "model": "groq/llama-3.3-70b-versatile",
                    "env_var": "GROQ_API_KEY",
                    "api_key_url": "https://console.groq.com/keys",
                    "description": "Extreme speed, supports large context (128k)",
                    "icon": "⚡"
                },
                "8": {
                    "name": "Groq GPT-OSS 20B",
                    "model": "groq/openai/gpt-oss-20b",
                    "env_var": "GROQ_API_KEY",
                    "api_key_url": "https://console.groq.com/keys",
                    "description": "Fast Open-Source Language Model",
                    "icon": "🚀"
                },
                "9": {
                    "name": "Step-3.5-Flash (Free)",
                    "model": "openrouter/stepfun/step-3.5-flash:free",
                    "env_var": "OPENROUTER_API_KEY",
                    "api_key_url": "https://openrouter.ai/keys",
                    "description": "Fast reasoning model with free tier access",
                    "icon": "⚡"
                },
                "10": {
                    "name": "Nvidia Nemotron (Free)",
                    "model": "openrouter/nvidia/nemotron-3-nano-30b-a3b:free",
                    "env_var": "OPENROUTER_API_KEY",
                    "api_key_url": "https://openrouter.ai/keys",
                    "description": "NVIDIA high-performance reasoning",
                    "icon": "🌩️"
                },
                "11": {
                    "name": "DeepSeek Chat",
                    "model": "deepseek/deepseek-chat",
                    "env_var": "DEEPSEEK_API_KEY",
                    "api_key_url": "https://platform.deepseek.com/api_keys",
                    "description": "Premium performance with competitive pricing",
                    "icon": "🐳"
                },
                "12": {
                    "name": "Gemma 4-E4B (Local)",
                    "model": "huggingface/google/gemma-4-E4B-it",
                    "env_var": "HF_TOKEN",
                    "api_key_url": "https://huggingface.co/settings/tokens",
                    "description": "Local execution via Transformers. HF Token is optional.",
                    "icon": "🏠"
                },
                "13": {
                    "name": "Qwen Cloud (Alibaba)",
                    "model": "openai/qwen-plus",
                    "env_var": "DASHSCOPE_API_KEY",
                    "api_key_url": "https://dashscope.console.aliyun.com/",
                    "description": "Flagship model by Alibaba Cloud (Recommended for Hackathon)",
                    "icon": "☁️",
                    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"
                }
            }
            with open(providers_file, 'w', encoding='utf-8') as f:
                json.dump(default_providers, f, indent=4)
        except Exception:
            pass

    # Load from config/providers.json
    if providers_file.exists():
        try:
            with open(providers_file, 'r', encoding='utf-8') as f:
                custom_providers = cast(Dict[str, Dict[str, str]], json.load(f))
                AI_PROVIDERS.clear()
                AI_PROVIDERS.update(custom_providers)
        except Exception:
            pass

# Initialize providers list
init_providers()


def get_env_file_path() -> Path:
    """Get the path to .env file in the project root"""
    return SCRIPT_DIR / ".env"


def load_env_file() -> None:
    """Load .env file and set environment variables in current process"""
    env_file = get_env_file_path()
    if env_file.exists() and load_dotenv:
        load_dotenv(env_file, override=True)
    elif env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")


def read_api_keys_from_file(file_path: str) -> List[str]:
    """Read API keys from a file (one per line)."""
    api_keys = []
    try:
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = SCRIPT_DIR / file_path

        if not full_path.exists():
            return []

        with open(full_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    api_keys.append(line)

        return api_keys
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")
        return []


def save_multiple_api_keys_to_env(api_keys: Dict[str, Any], active_provider: Optional[str] = None) -> bool:
    """Save multiple API keys to .env file and set active provider."""
    env_file = get_env_file_path()

    try:
        env_vars = {}
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        updates = {}
        for provider_key, api_key in api_keys.items():
            if provider_key in AI_PROVIDERS:
                provider = AI_PROVIDERS[provider_key]
                env_var = provider['env_var']
                if env_var not in updates:
                    updates[env_var] = []
                updates[env_var].append(api_key)

        for env_var, values in updates.items():
            current_val = env_vars.get(env_var, "")
            new_val = None
            for v in values:
                val_to_check = v[0] if isinstance(v, list) and v else v
                if val_to_check and str(val_to_check).strip() != str(current_val).strip():
                    new_val = v
                    break

            if new_val:
                if isinstance(new_val, list):
                    if new_val:
                        env_vars[env_var] = new_val[0]
                        env_vars[f"{env_var}_KEYS"] = '\n'.join(new_val)
                        env_vars[f"{env_var}_INDEX"] = '0'
                else:
                    env_vars[env_var] = str(new_val)
            else:
                is_all_empty = True
                for v in values:
                    val_to_check = v[0] if isinstance(v, list) and v else v
                    if val_to_check and str(val_to_check).strip():
                        is_all_empty = False
                        break

                if is_all_empty:
                    if env_var in env_vars:
                        del env_vars[env_var]
                    if f"{env_var}_KEYS" in env_vars:
                        del env_vars[f"{env_var}_KEYS"]
                    if f"{env_var}_INDEX" in env_vars:
                        del env_vars[f"{env_var}_INDEX"]
                else:
                    non_empty = None
                    for v in values:
                        val_to_check = v[0] if isinstance(v, list) and v else v
                        if val_to_check and str(val_to_check).strip():
                            non_empty = v
                            break

                    if non_empty:
                        if isinstance(non_empty, list):
                            env_vars[env_var] = non_empty[0]
                            env_vars[f"{env_var}_KEYS"] = '\n'.join(non_empty)
                            env_vars[f"{env_var}_INDEX"] = '0'
                        else:
                            env_vars[env_var] = str(non_empty)

        if not active_provider:
            current_model = env_vars.get('HADES_LLM', '')
            for pk, p in AI_PROVIDERS.items():
                if p['model'] == current_model:
                    active_provider = pk
                    break

        if active_provider and active_provider in AI_PROVIDERS:
            provider = AI_PROVIDERS[active_provider]
            env_var = provider['env_var']
            active_api_key = env_vars.get(env_var)

            if active_api_key:
                env_vars['LLM_API_KEY'] = active_api_key
                env_vars['HADES_LLM'] = provider['model']
                if provider.get('api_base'):
                    env_vars['LLM_API_BASE'] = provider['api_base']
                    env_vars['OPENAI_API_BASE'] = provider['api_base']
                else:
                    if 'LLM_API_BASE' in env_vars: del env_vars['LLM_API_BASE']
                    if 'OPENAI_API_BASE' in env_vars: del env_vars['OPENAI_API_BASE']
            else:
                if 'LLM_API_KEY' in env_vars: del env_vars['LLM_API_KEY']
                if 'HADES_LLM' in env_vars: del env_vars['HADES_LLM']
                if 'LLM_API_BASE' in env_vars: del env_vars['LLM_API_BASE']
                if 'OPENAI_API_BASE' in env_vars: del env_vars['OPENAI_API_BASE']
        elif api_keys:
            first_key = list(api_keys.keys())[0]
            provider = AI_PROVIDERS[first_key]
            first_api_key = api_keys[first_key]
            if isinstance(first_api_key, list) and first_api_key:
                env_vars['LLM_API_KEY'] = first_api_key[0]
            else:
                env_vars['LLM_API_KEY'] = first_api_key
            env_vars['HADES_LLM'] = provider['model']

        with open(env_file, 'w', encoding='utf-8') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
            f.write("\n")
            f.write("# HADES API Configuration\n")
            f.write("# Auto-generated by hades.py --setup-api\n")
            if active_provider and active_provider in AI_PROVIDERS:
                provider = AI_PROVIDERS[active_provider]
                f.write(f"# Active Provider: {provider['name']} ({provider['model']})\n")
            f.write("# All configured providers are saved above\n")

        load_env_file()
        return True
    except KeyError as e:
        console.print(f"[red]Error: Provider key '{e}' not found in API keys.[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error saving to .env file: {e}[/red]")
        console.print(f"[dim red]{traceback.format_exc()}[/dim red]")
        return False


def save_api_key_to_env(provider_key: str, api_key: str, model: str) -> bool:
    """Save API key to .env file."""
    env_file = get_env_file_path()

    try:
        env_vars = {}
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()

        env_vars[provider_key] = api_key
        env_vars['LLM_API_KEY'] = api_key
        env_vars['HADES_LLM'] = model

        if provider_key == 'GOOGLE_API_KEY':
            env_vars['GOOGLE_API_KEY'] = api_key

        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(f"{provider_key}={api_key}\n")
            f.write(f"LLM_API_KEY={api_key}\n")
            f.write(f"HADES_LLM={model}\n")

            if provider_key == 'GOOGLE_API_KEY':
                f.write(f"GOOGLE_API_KEY={api_key}\n")

            written_keys = {provider_key, 'LLM_API_KEY', 'HADES_LLM'}
            if provider_key == 'GOOGLE_API_KEY':
                written_keys.add('GOOGLE_API_KEY')

            for key, value in env_vars.items():
                if key not in written_keys:
                    f.write(f"{key}={value}\n")

            f.write("\n")
            f.write("# HADES API Configuration\n")
            f.write("# Auto-generated by hades.py --setup-api\n")
            f.write(f"# AI Provider: {model}\n")

        return True
    except Exception as e:
        console.print(f"[red]Error saving to .env file: {e}[/red]")
        return False


def display_api_setup_menu() -> Optional[str]:
    """Display interactive menu for API key setup"""
    console.print()

    table = Table(
        title="[bold cyan]Select AI Provider[/bold cyan]",
        show_header=True,
        header_style="bold bright_cyan",
        border_style="cyan",
        box=box.ROUNDED
    )
    table.add_column("Option", style="bold yellow", width=8, justify="center")
    table.add_column("Provider", style="bold green", width=30)
    table.add_column("Description", style="dim", width=45)
    table.add_column("Get API Key", style="dim cyan", width=25)

    for key, provider in AI_PROVIDERS.items():
        table.add_row(
            f"[bold]{key}[/bold]",
            f"{provider['icon']} {provider['name']}",
            provider['description'],
            provider['api_key_url']
        )

    console.print(table)
    console.print()

    provider_keys = list(AI_PROVIDERS.keys())
    choice = Prompt.ask(
        "[bold cyan]Select provider[/bold cyan]",
        choices=provider_keys,
        default="1"
    )

    return choice


def get_existing_api_keys() -> Dict[str, Dict[str, Any]]:
    """Get existing API keys from .env file"""
    existing = {}
    env_file = get_env_file_path()

    if not env_file.exists():
        return existing

    env_vars = {}
    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except Exception:
        return existing

    for provider_key, provider in AI_PROVIDERS.items():
        env_var = provider['env_var']
        keys_var = f"{env_var}_KEYS"
        index_var = f"{env_var}_INDEX"

        config = {
            "has_key": False,
            "env_var": env_var,
            "is_multiple": False,
            "count": 0,
            "current_index": 0
        }

        if keys_var in env_vars:
            api_keys = env_vars[keys_var].split('\n')
            api_keys = [k.strip() for k in api_keys if k.strip()]
            if api_keys:
                config["has_key"] = True
                config["is_multiple"] = True
                config["count"] = len(api_keys)
                config["current_index"] = int(env_vars.get(index_var, '0'))
        elif env_var in env_vars and env_vars[env_var]:
            config["has_key"] = True
            config["is_multiple"] = False
            config["count"] = 1
            config["current_index"] = 0

        if config["has_key"]:
            existing[provider_key] = config

    return existing


def setup_api_key_interactive() -> None:
    """Interactive API key setup with batch input and provider selection"""
    display_banner()

    existing_keys = get_existing_api_keys()
    has_existing = len(existing_keys) > 0

    if has_existing:
        existing_panel = Panel(
            f"[bold green]Found {len(existing_keys)} configured provider(s)[/bold green]\n\n"
            "You can:\n"
            "  1. Use existing configuration (select active provider)\n"
            "  2. Add/Update API keys for providers\n\n"
            "[dim]Existing providers will be shown with ✓ in the selection table.[/dim]",
            title="[bold yellow]Existing Configuration Detected[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(existing_panel)
        console.print()

        use_existing = Prompt.ask(
            "[bold cyan]What would you like to do?[/bold cyan]",
            choices=["1", "2"],
            default="1"
        )

        if use_existing == "1":
            console.print()
            console.print("[bold cyan]Select Active Provider[/bold cyan]\n")

            existing_table = Table(
                title="[bold yellow]Configured Providers[/bold yellow]",
                show_header=True,
                header_style="bold bright_yellow",
                border_style="yellow",
                box=box.ROUNDED
            )
            existing_table.add_column("Option", style="bold yellow", width=8, justify="center")
            existing_table.add_column("Provider", style="bold green", width=30)
            existing_table.add_column("Status", style="dim", width=30)
            existing_table.add_column("Keys", style="dim", width=15)

            env_file = get_env_file_path()
            current_active = ""
            if env_file.exists():
                try:
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('HADES_LLM='):
                                current_active = line.split('=', 1)[1].strip().strip('"').strip("'")
                                break
                except Exception:
                    pass

            for provider_key in sorted(existing_keys.keys(), key=int):
                provider = AI_PROVIDERS[provider_key]
                config = existing_keys[provider_key]
                is_active = current_active == provider['model']

                status_text = "[green]✓ Currently Active[/green]" if is_active else "[dim]Available[/dim]"
                keys_text = f"{config['count']} keys (using #{config['current_index'] + 1})" if config["is_multiple"] else "1 key"

                existing_table.add_row(
                    f"[bold]{provider_key}[/bold]",
                    f"{provider['icon']} {provider['name']}",
                    status_text,
                    keys_text
                )

            console.print(existing_table)
            console.print()

            selected = Prompt.ask(
                "[bold cyan]Select provider to activate[/bold cyan]",
                choices=sorted(existing_keys.keys(), key=int),
                default=sorted(existing_keys.keys(), key=int)[0]
            )

            if save_multiple_api_keys_to_env({}, active_provider=selected):
                provider = AI_PROVIDERS[selected]
                console.print()
                success_panel = Panel(
                    f"[bold green]✓ Active Provider Updated![/bold green]\n\n"
                    f"[yellow]Active Provider:[/yellow] {provider['icon']} {provider['name']}\n"
                    f"[yellow]Active Model:[/yellow] {provider['model']}\n\n"
                    f"[cyan]You can now run HADES with this provider.[/cyan]",
                    title="[bold green]Success[/bold green]",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(1, 2)
                )
                console.print(success_panel)
                return
            else:
                console.print("[red]Failed to update active provider[/red]")
                return

    else:
        welcome_panel = Panel(
            "[bold cyan]API Key Configuration Wizard[/bold cyan]\n\n"
            "You can configure multiple AI providers at once.\n"
            "Select providers by entering their numbers (e.g., 1,3,5 or 1 3 5).\n"
            "All API keys will be saved, and the provider you select will be automatically activated.\n\n"
            "[dim]You can add more providers later by running this setup again.[/dim]",
            title="[bold green]Welcome[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(welcome_panel)
        console.print()

    api_keys: Dict[str, Any] = {}
    configured_providers: List[str] = []

    console.print("[bold cyan]Step 1: Select Providers to Configure[/bold cyan]\n")

    provider_table = Table(
        title="[bold yellow]Available AI Providers[/bold yellow]",
        show_header=True,
        header_style="bold bright_yellow",
        border_style="yellow",
        box=box.ROUNDED
    )
    provider_table.add_column("Option", style="bold yellow", width=8, justify="center")
    provider_table.add_column("Provider", style="bold green", width=30)
    provider_table.add_column("Description", style="dim", width=45)
    provider_table.add_column("Status", style="dim", width=15)
    provider_table.add_column("Get API Key", style="dim cyan", width=25)

    env_file = get_env_file_path()
    env_vars = {}
    if env_file.exists():
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception:
            pass
            
def setup_notifications_interactive() -> None:
    """Interactive notification setup for Telegram and Discord"""
    display_banner()
    
    welcome_panel = Panel(
        "[bold cyan]Notification Setup Wizard[/bold cyan]\n\n"
        "Configure where HADES sends scan results and alerts.\n"
        "You can set up Telegram bots or Discord webhooks.\n\n"
        "[dim]Credentials will be stored securely in the config/ directory.[/dim]",
        title="[bold green]Alert System[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(welcome_panel)
    console.print()
    
    config_dir = SCRIPT_DIR / "config"
    config_dir.mkdir(exist_ok=True)
    
    # 1. Telegram Setup
    console.print("[bold cyan]Step 1: Telegram Notifications[/bold cyan]")
    console.print("[dim]Get a token from @BotFather on Telegram.[/dim]\n")
    
    token = Prompt.ask("[bold yellow]Enter Telegram Bot Token[/bold yellow] [dim](Leave empty to skip)[/dim]", default="")
    if token:
        chat_id = Prompt.ask("[bold yellow]Enter Telegram Chat ID[/bold yellow] [dim](Get from @userinfobot)[/dim]")
        
        with open(config_dir / "telegram_token.txt", "w", encoding='utf-8') as f:
            f.write(token.strip())
        with open(config_dir / "telegram_chat_id.txt", "w", encoding='utf-8') as f:
            f.write(chat_id.strip())
        console.print("[green]✓ Telegram configured![/green]\n")
    else:
        console.print("[dim]Skipping Telegram setup.[/dim]\n")
        
    # 2. Discord Setup
    console.print("[bold cyan]Step 2: Discord Notifications[/bold cyan]")
    webhook = Prompt.ask("[bold yellow]Enter Discord Webhook URL[/bold yellow] [dim](Leave empty to skip)[/dim]", default="")
    if webhook:
        with open(config_dir / "discord_webhook.txt", "w", encoding='utf-8') as f:
            f.write(webhook.strip())
        console.print("[green]✓ Discord configured![/green]\n")
    else:
        console.print("[dim]Skipping Discord setup.[/dim]\n")
        
    success_panel = Panel(
        "[bold green]✓ Notification Setup Complete![/bold green]\n\n"
        "HADES modules will now use these credentials to send alerts.\n"
        "You can re-run this setup anytime to update credentials.",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(success_panel)

    current_active = env_vars.get('HADES_LLM', '')

    for key, provider in AI_PROVIDERS.items():
        status = ""
        if key in existing_keys:
            config = existing_keys[key]
            if current_active == provider['model']:
                status = "[green]✓ Active[/green]"
            elif config["is_multiple"]:
                status = f"[yellow]✓ {config['count']} keys[/yellow]"
            else:
                status = "[yellow]✓ Set[/yellow]"
        else:
            status = "[dim]Not set[/dim]"

        provider_table.add_row(
            f"[bold]{key}[/bold]",
            f"{provider['icon']} {provider['name']}",
            provider['description'],
            status,
            provider['api_key_url']
        )

    console.print(provider_table)
    console.print()

    while True:
        selection_input = Prompt.ask(
            "[bold cyan]Enter provider numbers to configure[/bold cyan] (e.g., 1,3,5 or 1 3 5, or 'all' for all)",
            default="1"
        )

        selected_keys: List[str] = []
        if selection_input.lower().strip() == "all":
            selected_keys = list(AI_PROVIDERS.keys())
        else:
            numbers = re.findall(r'\d+', selection_input)
            for num in numbers:
                if num in AI_PROVIDERS:
                    if num not in selected_keys:
                        selected_keys.append(num)

        if selected_keys:
            break
        else:
            console.print("[red]Invalid selection. Please enter valid provider numbers.[/red]\n")

    console.print()
    console.print(f"[green]Selected {len(selected_keys)} provider(s) to configure[/green]\n")
    console.print("[bold cyan]Step 2: Enter API Keys[/bold cyan]\n")

    for key in selected_keys:
        provider = AI_PROVIDERS[key]

        info_text = Text()
        info_text.append(f"{provider['icon']} ", style="")
        info_text.append(f"{provider['name']}", style="bold green")
        info_text.append(f" - {provider['description']}\n", style="dim")
        info_text.append(f"Get API key: ", style="dim")
        info_text.append(f"{provider['api_key_url']}", style="dim cyan")

        info_panel = Panel(info_text, border_style="cyan", box=box.ROUNDED, padding=(0, 1))
        console.print(info_panel)

        console.print("[dim yellow]💡 Tip: You can input a file containing multiple API keys (one per line) for auto-rotation[/dim yellow]\n")
        input_method = Prompt.ask(
            f"[bold cyan]Input method for {provider['name']}[/bold cyan] (1=Single API key, 2=File with multiple keys)",
            choices=["1", "2"],
            default="1"
        )

        if input_method == "1":
            api_key = Prompt.ask(
                f"[bold cyan]Enter {provider['name']} API key[/bold cyan] (or press Enter to skip)",
                password=True,
                default=""
            )

            if api_key and len(api_key.strip()) >= 10:
                api_keys[key] = api_key.strip()
                configured_providers.append(key)
                console.print(f"[green]✓ {provider['name']} API key saved[/green]\n")
            else:
                console.print(f"[dim]⊘ {provider['name']} skipped[/dim]\n")
        else:
            console.print("[dim]File format: One API key per line (empty lines and lines starting with # are ignored)[/dim]\n")
            file_path = Prompt.ask(
                f"[bold cyan]Enter path to file containing {provider['name']} API keys[/bold cyan] (one per line)",
                default=""
            )

            if file_path and file_path.strip():
                api_keys_list = read_api_keys_from_file(file_path.strip())

                if api_keys_list:
                    valid_keys = [k.strip() for k in api_keys_list if k.strip() and len(k.strip()) >= 10]

                    if valid_keys:
                        api_keys[key] = valid_keys
                        configured_providers.append(key)
                        console.print(f"[green]✓ {provider['name']}: {len(valid_keys)} API key(s) loaded from file[/green]\n")
                        console.print(f"[dim]Keys will automatically rotate when rate limited[/dim]\n")
                    else:
                        console.print(f"[red]✗ No valid API keys found in file (minimum 10 characters)[/red]\n")
                else:
                    console.print(f"[red]✗ Could not read API keys from file or file is empty[/red]\n")
            else:
                console.print(f"[dim]⊘ {provider['name']} skipped[/dim]\n")

    if not api_keys:
        error_panel = Panel(
            "[bold red]✗ No API Keys Entered[/bold red]\n\n"
            "Please enter at least one API key to continue.",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)

    console.print()
    console.print("[bold cyan]Step 3: Select Active Provider[/bold cyan]\n")

    active_table = Table(
        title="[bold yellow]Configured Providers[/bold yellow]",
        show_header=True,
        header_style="bold bright_yellow",
        border_style="yellow",
        box=box.ROUNDED
    )
    active_table.add_column("Option", style="bold yellow", width=8, justify="center")
    active_table.add_column("Provider", style="bold green", width=25)
    active_table.add_column("Model", style="dim", width=30)
    active_table.add_column("Description", style="dim", width=40)

    for key in configured_providers:
        provider = AI_PROVIDERS[key]
        active_table.add_row(
            f"[bold]{key}[/bold]",
            f"{provider['icon']} {provider['name']}",
            provider['model'],
            provider['description']
        )

    console.print(active_table)
    console.print()

    active_provider = Prompt.ask(
        "[bold yellow]Select provider to activate[/bold yellow]",
        choices=configured_providers,
        default=configured_providers[0]
    )

    console.print()
    if not Confirm.ask(f"[bold yellow]Save all API keys and activate {AI_PROVIDERS[active_provider]['name']}?[/bold yellow]"):
        console.print("[yellow]Setup cancelled by user[/yellow]")
        sys.exit(0)

    console.print()
    console.print("[cyan]Saving configuration...[/cyan]")

    success = save_multiple_api_keys_to_env(api_keys, active_provider)

    if success:
        active_provider_info = AI_PROVIDERS[active_provider]
        active_llm = os.getenv('HADES_LLM')
        active_api_key = os.getenv('LLM_API_KEY')
        active_provider_key_value = api_keys[active_provider]

        if isinstance(active_provider_key_value, list) and active_provider_key_value:
            primary_key: str = active_provider_key_value[0]
        else:
            primary_key = str(active_provider_key_value)

        is_active = bool(active_llm == active_provider_info['model'] and active_api_key == primary_key)

        provider_info = f"[yellow]Configured Providers:[/yellow] {len(configured_providers)}\n"
        provider_info += f"[yellow]Active Provider:[/yellow] {active_provider_info['icon']} {active_provider_info['name']}\n"
        provider_info += f"[yellow]Active Model:[/yellow] {active_provider_info['model']}\n"

        if isinstance(active_provider_key_value, list):
            provider_info += f"[yellow]API Keys Loaded:[/yellow] {len(active_provider_key_value)} keys (auto-rotation enabled)\n"

        provider_info += f"[yellow]Status:[/yellow] {'[green]✓ Active in current session[/green]' if is_active else '[yellow]⚠ Saved to .env file[/yellow]'}\n"
        provider_info += f"[yellow]Saved to:[/yellow] {get_env_file_path()}\n\n"
        provider_info += f"[cyan]Next Steps:[/cyan]\n"
        provider_info += f"1. Run HADES: [bold]hades --target <url>[/bold]\n"
        provider_info += f"2. Configuration is automatically loaded from .env file\n\n"
        provider_info += f"[dim]Tip: You can change active provider by running: hades.py --setup-api[/dim]"

        success_panel = Panel(
            f"[bold green]✓ Configuration Saved and Activated![/bold green]\n\n{provider_info}",
            title="[bold green]Success[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(success_panel)

        if not is_active:
            console.print()
            info_panel = Panel(
                f"[bold yellow]Note:[/bold yellow] Environment variables have been saved to .env file.\n"
                f"For new terminal sessions, the .env file will be automatically loaded.\n\n"
                f"[dim]If you need to use in current session, restart the terminal or run:[/dim]\n"
                f"[dim]export $(grep -v '^#' {get_env_file_path()} | xargs)[/dim]",
                border_style="yellow",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            console.print(info_panel)
    else:
        error_panel = Panel(
            "[bold red]✗ Failed to Save Configuration[/bold red]\n\n"
            "Please check file permissions and try again.",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)


# ============================================================================
# Banner Display
# ============================================================================

def display_banner() -> None:
    """Minimal, elegant banner — Kali tool style."""
    console.print()
    console.print("[bold red]██╗  ██╗ █████╗ ██████╗ ███████╗███████╗[/bold red]")
    console.print("[bold red]██║  ██║██╔══██╗██╔══██╗██╔════╝██╔════╝[/bold red]")
    console.print("[bold red]███████║███████║██║  ██║█████╗  ███████╗[/bold red]")
    console.print("[bold red]██╔══██║██╔══██║██║  ██║██╔══╝  ╚════██║[/bold red]")
    console.print("[bold red]██║  ██║██║  ██║██████╔╝███████╗███████║[/bold red]")
    console.print("[bold red]╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚══════╝╚══════╝[/bold red]")
    console.print()

    # Meta Info
    meta = Table.grid(padding=(0, 2))
    meta.add_column(justify="right", style="cyan")
    meta.add_column(justify="left", style="white")
    
    meta.add_row("VERSION :", f"[bold yellow]v{VERSION}[/bold yellow]")
    meta.add_row("AUTHOR  :", f"[bold white]{AUTHOR}[/bold white]")
    meta.add_row("EDITION :", "[bold magenta]Modern Pro Edition[/bold magenta]")
    
    # Right side meta
    meta_right = Table.grid(padding=(0, 2))
    meta_right.add_column(justify="right", style="cyan")
    meta_right.add_column(justify="left", style="white")
    meta_right.add_row("MODES :", "AI Agent | Shell Module")
    meta_right.add_row("USAGE :", "[dim]hades [OPTIONS] [TARGET][/dim]")
    
    # Combine
    combined = Table.grid(padding=(0, 10))
    combined.add_row(meta, meta_right)
    
    console.print(combined)
    console.print("[dim]" + "─" * 70 + "[/dim]\n")


# ============================================================================
# Help Display
# ============================================================================

def display_help() -> None:
    """Help formatted like nmap/sqlmap — clear columns, tagged categories."""
    display_banner()

    def section(title: str) -> None:
        console.print(f"\n[bold red] {title}[/bold red]")
        console.print("[dim]" + "─" * 62 + "[/dim]")

    def row(short: str, long: str, arg: str, desc: str, tag: str, tag_color: str = "cyan") -> None:
        short_s = f"[bold red]{short:<4}[/bold red]" if short else "    "
        long_s  = f"[bold cyan]{long:<22}[/bold cyan]"
        arg_s   = f"[yellow]{arg:<14}[/yellow]" if arg else " " * 14
        desc_s  = f"[white]{desc}[/white]"
        tag_s   = f"[{tag_color}][{tag}][/{tag_color}]"
        console.print(f"  {short_s} {long_s} {arg_s} {desc_s:<38} {tag_s}")

    # ── AI Agent Mode ──────────────────────────────────────────────────────────
    section("AI AGENT MODE")
    row("-t",  "--target",          "<url>+",   "Target URL/domain/path (repeatable)",       "AI",       "blue")
    row("",    "--instruction",     "<text>",   "Custom instructions for the AI agent",      "AI",       "blue")
    row("",    "--templates",       "<name>",   "Use or manage a saved instruction template","AI",       "blue")
    row("",    "--run-name",        "<name>",   "Label for this scan session",               "AI",       "blue")
    row("-n",  "--non-interactive", "",         "Headless mode — no interactive prompts",    "AI",       "blue")

    # ── Reconnaissance ─────────────────────────────────────────────────────────
    section("RECONNAISSANCE")
    row("-d",  "--mass-recon",      "",         "Mass recon — subfinder + httpx + WAF detect","RECON",  "green")
    row("-s",  "--single-recon",    "",         "Deep single-target recon",                  "RECON",   "green")
    row("-f",  "--port-scan",       "",         "Port scanning & service detection (nmap)",  "RECON",   "green")

    # ── Injection Testing ──────────────────────────────────────────────────────
    section("INJECTION TESTING")
    row("-p",  "--mass-sql",        "",         "Mass SQL injection across targets",         "SQLi",    "red")
    row("-o",  "--single-sql",      "",         "Single target SQL injection (sqlmap)",      "SQLi",    "red")
    row("-w",  "--mass-xss",        "",         "Mass XSS testing with dalfox",             "XSS",     "red")
    row("-x",  "--single-xss",      "",         "Single target XSS with custom payloads",   "XSS",     "red")
    row("-j",  "--single-lfi",      "",         "Local File Inclusion / path traversal",    "LFI",     "red")

    # ── Special Operations ─────────────────────────────────────────────────────
    section("SPECIAL OPERATIONS")
    row("-m",  "--mass-assess",     "",         "Mass vuln assessment with nuclei",         "VULN",    "magenta")
    row("-y",  "--sub-takeover",    "",         "Subdomain takeover detection",             "TAKEOVER","magenta")
    row("-q",  "--dir-patrol",      "",         "Directory & file enumeration (ffuf)",      "DIR",     "magenta")
    row("-l",  "--js-finder",       "",         "Extract secrets from JavaScript files",    "SECRETS", "magenta")
    row("-k",  "--mass-cors",       "",         "Mass CORS misconfiguration testing",       "CORS",    "magenta")

    # ── System ─────────────────────────────────────────────────────────────────
    section("SYSTEM")
    row("",    "--setup-api",       "",         "AI provider & API key wizard",             "CONFIG",  "dim")
    row("",    "--setup-telegram",  "",         "Telegram & Discord notification setup",    "NOTIFY",  "dim")
    row("-i",  "--install",         "",         "Install Python deps + system tools",       "SETUP",   "dim")
    row("",    "--web",             "",         "Launch web dashboard at localhost:9656",   "WEB",     "dim")
    row("",    "--docker-setup",    "",         "Docker status check & installation guide", "DOCKER",  "dim")
    row("",    "--flush-db",        "",         "Wipe all database records",                "DB",      "dim")
    row("-h",  "--help",            "",         "Show this help message",                   "HELP",    "dim")

    # ── Template Subcommands ───────────────────────────────────────────────────
    section("TEMPLATE SUBCOMMANDS  (--templates <cmd>)")
    row("",    "list",              "",         "Show all saved templates",                 "TPL",     "dim")
    row("",    "create",            "",         "Create a new template interactively",      "TPL",     "dim")
    row("",    "edit <name>",       "",         "Edit an existing template",                "TPL",     "dim")
    row("",    "delete <name>",     "",         "Delete a template",                        "TPL",     "dim")
    row("",    "show <name>",       "",         "Print template content to terminal",       "TPL",     "dim")

    # ── Examples ───────────────────────────────────────────────────────────────
    section("EXAMPLES")
    examples = [
        ("hades --target https://example.com",                        "start AI agent scan"),
        ("hades -t app.io --instruction 'Focus on SQLi and IDOR'",   "custom instruction"),
        ("hades -t target.com --templates full_audit -n",            "template + CI mode"),
        ("hades -t site.com -t ./local-api",                         "multi-target scan"),
        ("hades -d",                                                  "mass recon module"),
        ("hades -p",                                                  "mass SQL injection"),
        ("hades -l",                                                  "JS secret finder"),
        ("hades --setup-api",                                         "configure AI provider"),
        ("hades --setup-telegram",                                    "configure telegram alerts"),
        ("hades --templates list",                                    "manage templates"),
        ("hades --web",                                               "open web dashboard"),
    ]
    for cmd, note in examples:
        console.print(f"  [green]$[/green] [cyan]{cmd:<60}[/cyan] [dim]# {note}[/dim]")

    console.print()
    console.print("[dim]  Use only on systems you have explicit written authorization to test.[/dim]")
    console.print()


# ============================================================================
# Shell Module Mode Map
# ============================================================================

SHELL_MODULE_MAP: Dict[str, str] = {
    # Reconnaissance
    "-d": "modules/recon/mass_reconnaissance.sh",
    "--mass-recon": "modules/recon/mass_reconnaissance.sh",
    "-s": "modules/recon/single_reconnaissance.sh",
    "--single-recon": "modules/recon/single_reconnaissance.sh",
    "-f": "modules/recon/port_scanning.sh",
    "--port-scan": "modules/recon/port_scanning.sh",

    # Injection
    "-p": "modules/injection/mass_sql_injection.sh",
    "--mass-sql": "modules/injection/mass_sql_injection.sh",
    "-o": "modules/injection/single_sql_injection.sh",
    "--single-sql": "modules/injection/single_sql_injection.sh",
    "-w": "modules/injection/mass_xss_testing.sh",
    "--mass-xss": "modules/injection/mass_xss_testing.sh",
    "-x": "modules/injection/single_xss_testing.sh",
    "--single-xss": "modules/injection/single_xss_testing.sh",
    "-j": "modules/injection/local_file_inclusion.sh",
    "--single-lfi": "modules/injection/local_file_inclusion.sh",

    # Special Operations
    "-m": "modules/special/mass_vulnerability_assessment.sh",
    "--mass-assess": "modules/special/mass_vulnerability_assessment.sh",
    "-y": "modules/special/subdomain_takeover_detection.sh",
    "--sub-takeover": "modules/special/subdomain_takeover_detection.sh",
    "-q": "modules/special/directory_enumeration.sh",
    "--dir-patrol": "modules/special/directory_enumeration.sh",
    "-l": "modules/special/javascript_secret_finder.sh",
    "--js-finder": "modules/special/javascript_secret_finder.sh",
    "-k": "modules/special/mass_cors_testing.sh",
    "--mass-cors": "modules/special/mass_cors_testing.sh",
}

# Mapping of modules to their required binary tools
MODULE_REQUIRED_TOOLS: Dict[str, List[str]] = {
    "-d": ["subfinder", "assetfinder", "httprobe", "waybackurls", "anew", "ffuf", "wafw00f"],
    "--mass-recon": ["subfinder", "assetfinder", "httprobe", "waybackurls", "anew", "ffuf", "wafw00f"],
    "-s": ["nmap", "httpx", "subfinder"],
    "--single-recon": ["nmap", "httpx", "subfinder"],
    "-f": ["nmap"],
    "--port-scan": ["nmap"],
    "-p": ["sqlmap", "ghauri"],
    "--mass-sql": ["sqlmap", "ghauri"],
    "-o": ["sqlmap"],
    "--single-sql": ["sqlmap"],
    "-w": ["dalfox"],
    "--mass-xss": ["dalfox"],
    "-x": ["dalfox"],
    "--single-xss": ["dalfox"],
    "-j": ["ffuf"],
    "--single-lfi": ["ffuf"],
    "-m": ["nuclei"],
    "--mass-assess": ["nuclei"],
    "-y": ["subjack", "subfinder"],
    "--sub-takeover": ["subjack", "subfinder"],
    "-q": ["dirsearch"],
    "--dir-patrol": ["dirsearch"],
    "-l": ["jsfinder"],
    "--js-finder": ["jsfinder"],
    "-k": ["corscanner"],
    "--mass-cors": ["corscanner"]
}


# ============================================================================
# AI Agent Mode Functions
# ============================================================================

def check_ai_agent_mode_available() -> bool:
    """Check if AI agent mode dependencies are available."""
    try:
        import hades.interface.main
        return True
    except ImportError:
        return False


def check_ai_agent_dependencies() -> Dict[str, bool]:
    """Check which AI Agent Mode dependencies are installed."""
    dependency_map = {
        "rich": "rich",
        "pyyaml": "yaml",
        "litellm": "litellm",
        "openai": "openai",
        "tenacity": "tenacity",
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "pydantic": "pydantic",
        "playwright": "playwright",
        "docker": "docker",
        "textual": "textual",
        "requests": "requests",
        "jinja2": "jinja2",
    }

    dependencies = {}
    for package_name, import_name in dependency_map.items():
        try:
            __import__(import_name)
            dependencies[package_name] = True
        except ImportError:
            dependencies[package_name] = False

    return dependencies


def install_ai_agent_dependencies() -> bool:
    """Install AI Agent Mode dependencies using pip."""
    try:
        console.print("[cyan]Installing AI Agent Mode dependencies...[/cyan]")
        console.print("[dim]This may take a few minutes...[/dim]\n")

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(SCRIPT_DIR / "requirements.txt"), "--break-system-packages"],
            cwd=SCRIPT_DIR,
            text=True
        )

        if result.returncode == 0:
            console.print("[green]✓ Python packages installed successfully[/green]")

            console.print("\n[cyan]Installing Playwright browsers...[/cyan]")
            console.print("[dim]This may take additional time...[/dim]\n")
            playwright_result = subprocess.run(
                [sys.executable, "-m", "playwright", "install"],
                cwd=SCRIPT_DIR,
                text=True
            )

            if playwright_result.returncode == 0:
                console.print("[green]✓ Playwright browsers installed successfully[/green]")
            else:
                console.print("[yellow]⚠ Playwright browser installation had issues, but packages are installed[/yellow]")

            return True
        else:
            console.print(f"[red]✗ Error installing dependencies[/red]")
            return False
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        return False


def check_docker_setup() -> Dict[str, Any]:
    """Check Docker installation and setup status."""
    status = {
        "docker_installed": False,
        "docker_running": False,
        "docker_image_available": False,
        "docker_image_name": os.getenv("HADES_IMAGE", "ghcr.io/joelindra/hades-sandbox-now:latest"),
        "error": None,
    }

    try:
        import docker
        status["docker_installed"] = True

        try:
            client = docker.from_env()
            client.ping()
            status["docker_running"] = True

            try:
                image_name = status["docker_image_name"]
                client.images.get(image_name)
                status["docker_image_available"] = True
            except Exception:
                status["docker_image_available"] = False

        except Exception as e:
            status["error"] = str(e)
            status["docker_running"] = False

    except ImportError:
        status["error"] = "Docker Python library not installed"
        status["docker_installed"] = False

    return status


def display_docker_setup_guide() -> None:
    """Display comprehensive Docker setup guide"""
    display_banner()

    docker_status = check_docker_setup()

    status_table = Table(
        title="[bold cyan]Docker Status Check[/bold cyan]",
        show_header=True,
        header_style="bold bright_cyan",
        border_style="cyan",
        box=box.ROUNDED
    )
    status_table.add_column("Component", style="bold", width=30)
    status_table.add_column("Status", style="", width=20)

    docker_installed_status = "[green]✓ Installed[/green]" if docker_status["docker_installed"] else "[red]✗ Not Installed[/red]"
    docker_running_status = "[green]✓ Running[/green]" if docker_status["docker_running"] else "[red]✗ Not Running[/red]"
    image_status = "[green]✓ Available[/green]" if docker_status["docker_image_available"] else "[yellow]⚠ Not Pulled[/yellow]"

    status_table.add_row("Docker Engine", docker_installed_status)
    status_table.add_row("Docker Daemon", docker_running_status)
    status_table.add_row("HADES Image", image_status)

    console.print(status_table)
    console.print()

    install_panel = Panel(
        "[bold cyan]Docker Installation Guide[/bold cyan]\n\n"
        "[yellow]1. Install Docker Engine/Desktop:[/yellow]\n\n"
        "[bold]Linux (Ubuntu/Debian):[/bold]\n"
        "  [dim]curl -fsSL https://get.docker.com -o get-docker.sh[/dim]\n"
        "  [dim]sudo sh get-docker.sh[/dim]\n"
        "  [dim]sudo usermod -aG docker $USER[/dim]\n"
        "  [dim]newgrp docker  # or logout/login[/dim]\n\n"
        "[bold]macOS:[/bold]\n"
        "  [dim]Download Docker Desktop from: https://www.docker.com/products/docker-desktop[/dim]\n\n"
        "[bold]Windows (WSL2):[/bold]\n"
        "  [dim]Install Docker Desktop for Windows with WSL2 integration[/dim]\n\n"
        "[yellow]2. Verify Installation:[/yellow]\n"
        "  [dim]docker --version && docker info && docker ps[/dim]\n\n"
        "[yellow]3. Pull HADES Docker Image:[/yellow]\n"
        f"  [dim]docker pull {docker_status['docker_image_name']}[/dim]",
        title="[bold green]Docker Setup[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(install_panel)
    console.print()

    image_panel = Panel(
        f"[bold magenta]Docker Image Information[/bold magenta]\n\n"
        f"[yellow]Image Name:[/yellow] {docker_status['docker_image_name']}\n"
        f"[yellow]Purpose:[/yellow] Sandbox environment for AI Agent Mode\n"
        f"[yellow]Contains:[/yellow] Kali Linux + Security tools (nmap, subfinder, nuclei, etc.)\n\n"
        f"[cyan]This image provides:[/cyan]\n"
        f"• Isolated execution environment\n"
        f"• Pre-installed security tools\n"
        f"• Tool server for AI agents\n"
        f"• Network isolation for safe testing",
        title="[bold magenta]Image Details[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(image_panel)
    console.print()

    if docker_status["error"] or not docker_status["docker_running"]:
        troubleshooting_panel = Panel(
            "[bold yellow]Troubleshooting[/bold yellow]\n\n"
            f"[red]Current Issue:[/red] {docker_status.get('error', 'Docker not running')}\n\n"
            "[cyan]Common Solutions:[/cyan]\n"
            "1. Start Docker daemon:\n"
            "   [dim]Linux: sudo systemctl start docker[/dim]\n"
            "   [dim]macOS/Windows: Start Docker Desktop app[/dim]\n\n"
            "2. Verify user permissions:\n"
            "   [dim]Linux: sudo usermod -aG docker $USER[/dim]\n\n"
            "3. Restart Docker:\n"
            "   [dim]sudo systemctl restart docker[/dim] (Linux)",
            title="[bold yellow]Troubleshooting[/bold yellow]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(troubleshooting_panel)
        console.print()

    if docker_status["docker_running"] and docker_status["docker_image_available"]:
        success_panel = Panel(
            "[bold green]✓ Docker Setup Complete![/bold green]\n\n"
            "Docker is properly configured and ready to use.\n"
            "You can now run AI Agent Mode with Docker sandbox.",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(success_panel)


def check_shell_tools_available() -> Dict[str, bool]:
    """Check which Shell Module Mode tools are available."""
    tools = {
        "subfinder": False,
        "nmap": False,
        "httpx": False,
        "nuclei": False,
        "ffuf": False,
        "amass": False,
        "assetfinder": False,
        "httprobe": False,
        "waybackurls": False,
        "massdns": False,
    }

    for tool in tools.keys():
        try:
            result = subprocess.run(["which", tool], capture_output=True, text=True, timeout=2)
            tools[tool] = result.returncode == 0
        except Exception:
            tools[tool] = False

    return tools


def install_shell_module_dependencies() -> bool:
    """Install Shell Module Mode dependencies using bash script."""
    script_path = SCRIPT_DIR / "modules" / "system" / "install_dependencies.sh"

    if not script_path.exists():
        console.print(f"[red]Installation script not found: {script_path}[/red]")
        return False

    try:
        console.print("[cyan]Installing Shell Module Mode dependencies...[/cyan]")
        console.print("[dim]This may require system administrator privileges...[/dim]\n")

        result = subprocess.run(
            ["bash", str(script_path)],
            cwd=SCRIPT_DIR,
            check=False
        )

        return result.returncode == 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False


def install_dependencies_interactive() -> None:
    """Interactive dependency installation with mode selection"""
    display_banner()

    welcome_panel = Panel(
        "[bold cyan]Dependency Installation Wizard[/bold cyan]\n\n"
        "HADES has two operation modes, each requiring different dependencies:\n\n"
        "[bold]🤖 AI Agent Mode:[/bold] Python packages for AI-powered testing\n"
        "[bold]🔧 Shell Module Mode:[/bold] System tools for traditional modules\n\n"
        "Select which mode's dependencies you want to install.",
        title="[bold green]Welcome[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(welcome_panel)
    console.print()

    install_table = Table(
        title="[bold cyan]Select Installation Mode[/bold cyan]",
        show_header=True,
        header_style="bold bright_cyan",
        border_style="cyan",
        box=box.ROUNDED
    )
    install_table.add_column("Option", style="bold yellow", width=8, justify="center")
    install_table.add_column("Mode", style="bold green", width=25)
    install_table.add_column("Dependencies", style="dim", width=50)
    install_table.add_column("Status", style="dim", width=20)

    ai_deps = check_ai_agent_dependencies()
    ai_installed = sum(ai_deps.values())
    ai_total = len(ai_deps)
    ai_status = f"[green]{ai_installed}/{ai_total} installed[/green]" if ai_installed == ai_total else f"[yellow]{ai_installed}/{ai_total} installed[/yellow]"

    install_table.add_row(
        "[bold]1[/bold]",
        "🤖 AI Agent Mode",
        "Python packages (rich, litellm, playwright, docker, etc.)",
        ai_status
    )
    install_table.add_row(
        "[bold]2[/bold]",
        "🔧 Shell Module Mode",
        "System tools (nmap, subfinder, httpx, etc.)",
        "[dim]System tools[/dim]"
    )
    install_table.add_row(
        "[bold]3[/bold]",
        "📦 Both Modes",
        "Install all dependencies for both modes",
        "[dim]All[/dim]"
    )

    console.print(install_table)
    console.print()

    choice = Prompt.ask(
        "[bold cyan]Select installation mode[/bold cyan]",
        choices=["1", "2", "3"],
        default="1"
    )

    console.print()
    success = False

    if choice == "1":
        console.print("[bold cyan]Installing AI Agent Mode Dependencies[/bold cyan]\n")

        deps_table = Table(
            title="[bold yellow]Dependency Status[/bold yellow]",
            show_header=True,
            header_style="bold bright_yellow",
            border_style="yellow",
            box=box.SIMPLE,
            show_edge=True
        )
        deps_table.add_column("Dependency", style="bold", width=20)
        deps_table.add_column("Status", style="", width=15)

        for dep, installed in ai_deps.items():
            status = "[green]✓ Installed[/green]" if installed else "[red]✗ Missing[/red]"
            deps_table.add_row(dep, status)

        console.print(deps_table)
        console.print()

        if not Confirm.ask("[bold yellow]Proceed with installation?[/bold yellow]"):
            console.print("[yellow]Installation cancelled[/yellow]")
            sys.exit(0)

        success = install_ai_agent_dependencies()

    elif choice == "2":
        console.print("[bold cyan]Installing Shell Module Mode Dependencies[/bold cyan]\n")

        tools_status = check_shell_tools_available()
        available_count = sum(tools_status.values())
        total_count = len(tools_status)

        tools_table = Table(
            title="[bold yellow]Tool Availability Status[/bold yellow]",
            show_header=True,
            header_style="bold bright_yellow",
            border_style="yellow",
            box=box.SIMPLE,
            show_edge=True
        )
        tools_table.add_column("Tool", style="bold", width=20)
        tools_table.add_column("Status", style="", width=15)

        for tool, available in tools_status.items():
            status = "[green]✓ Available[/green]" if available else "[red]✗ Missing[/red]"
            tools_table.add_row(tool, status)

        console.print(tools_table)
        console.print()

        info_panel = Panel(
            "[bold yellow]Shell Module Mode Dependencies[/bold yellow]\n\n"
            "This will install system tools required for traditional security modules:\n"
            "• Network scanning tools (nmap, masscan)\n"
            "• Subdomain enumeration (subfinder, amass)\n"
            "• HTTP tools (httpx, curl)\n"
            "• Other security testing utilities\n\n"
            f"[dim]Current status: {available_count}/{total_count} tools available[/dim]\n"
            "[dim]Note: This may require sudo/administrator privileges[/dim]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(info_panel)
        console.print()

        if not Confirm.ask("[bold yellow]Proceed with installation?[/bold yellow]"):
            console.print("[yellow]Installation cancelled[/yellow]")
            sys.exit(0)

        success = install_shell_module_dependencies()

        if success:
            console.print()
            console.print("[cyan]Verifying installation...[/cyan]\n")
            tools_status_after = check_shell_tools_available()
            available_after = sum(tools_status_after.values())

            if available_after > available_count:
                console.print(f"[green]✓ Installation successful! {available_after}/{total_count} tools now available[/green]")
            else:
                console.print(f"[yellow]⚠ Some tools may still be missing. {available_after}/{total_count} tools available[/yellow]")
                console.print("[dim]You may need to add Go tools to PATH: export PATH=$PATH:~/go/bin[/dim]")

    elif choice == "3":
        console.print("[bold cyan]Installing All Dependencies[/bold cyan]\n")

        if not Confirm.ask("[bold yellow]Install dependencies for both modes?[/bold yellow]"):
            console.print("[yellow]Installation cancelled[/yellow]")
            sys.exit(0)

        console.print()
        console.print("[bold]Step 1: Installing AI Agent Mode dependencies...[/bold]\n")
        ai_success = install_ai_agent_dependencies()

        console.print()
        console.print("[bold]Step 2: Installing Shell Module Mode dependencies...[/bold]\n")
        shell_success = install_shell_module_dependencies()

        success = ai_success and shell_success

    console.print()
    if success:
        success_panel = Panel(
            "[bold green]✓ Installation Completed Successfully![/bold green]\n\n"
            "You can now use HADES with the installed dependencies.\n\n"
            "[cyan]Next Steps:[/cyan]\n"
            "• For AI Agent Mode: [bold]python hades.py --target <url>[/bold]\n"
            "• For Shell Module Mode: [bold]python hades.py -p[/bold] (or any module option)",
            title="[bold green]Success[/bold green]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(success_panel)
    else:
        error_panel = Panel(
            "[bold red]✗ Installation Failed[/bold red]\n\n"
            "Please check the error messages above and try again.\n\n"
            "[yellow]Common Issues:[/yellow]\n"
            "• Missing pip or Python packages\n"
            "• Insufficient permissions (try with sudo/admin)\n"
            "• Network connectivity issues\n"
            "• Missing system dependencies",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2)
        )
        console.print(error_panel)
        sys.exit(1)


def run_ai_agent_mode(args: argparse.Namespace) -> None:
    """Run AI Agent Mode by calling hades.interface.main."""
    original_argv = None
    try:
        original_argv = sys.argv.copy()

        new_argv = ['hades']

        if args.target:
            for target in args.target:
                new_argv.extend(['--target', target])

        instruction_to_use = args.instruction

        if hasattr(args, 'templates') and args.templates:
            try:
                from hades.templates.manager import read_template
                template_content = read_template(args.templates)
                if template_content:
                    if instruction_to_use:
                        instruction_to_use = f"{instruction_to_use}\n\n{template_content}"
                        console.print(f"[yellow]⚠ Both --instruction and --templates provided. Combining them.[/yellow]")
                    else:
                        instruction_to_use = template_content
                    console.print(f"[green]✓ Loaded template: {args.templates}[/green]")
                else:
                    console.print(f"[red]✗ Template '{args.templates}' not found[/red]")
                    sys.exit(1)
            except Exception as e:
                console.print(f"[red]Error loading template: {e}[/red]")
                sys.exit(1)

        if instruction_to_use:
            new_argv.extend(['--instruction', instruction_to_use])

        if args.run_name:
            new_argv.extend(['--run-name', args.run_name])

        if args.non_interactive:
            new_argv.append('--non-interactive')

        sys.argv = new_argv

        from hades.interface.main import main as ai_main
        ai_main()

    except ImportError as e:
        error_panel = Panel(
            f"[bold red]✗ AI Agent Mode Not Available[/bold red]\n\n"
            f"[yellow]Missing Dependencies[/yellow]\n\n"
            f"[cyan]Installation Command:[/cyan]\n"
            f"[bold]  pip install -r requirements.txt --break-system-packages[/bold]\n\n"
            f"[dim]Error Details: {e}[/dim]",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)
    except Exception as e:
        error_panel = Panel(
            f"[bold red]✗ Error Running AI Agent Mode[/bold red]\n\n"
            f"[yellow]Error:[/yellow] {e}\n\n"
            f"[dim]See traceback below for details[/dim]",
            title="[bold red]Fatal Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        console.print_exception()
        sys.exit(1)
    finally:
        if original_argv is not None:
            sys.argv = original_argv


# ============================================================================
# Shell Module Mode Functions
# ============================================================================

def run_shell_module_mode(module: str) -> None:
    """Run Shell Module Mode with enhanced error handling and display."""
    script_path = SHELL_MODULE_MAP.get(module)

    if not script_path:
        error_panel = Panel(
            f"[bold red]✗ Invalid Shell Module[/bold red]\n\n"
            f"[yellow]Module:[/yellow] {module}\n\n"
            f"[cyan]Use 'hades.py --help' to see all available modules[/cyan]",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)

    full_path = SCRIPT_DIR / script_path

    if not full_path.exists():
        error_panel = Panel(
            f"[bold red]✗ Module Script Not Found[/bold red]\n\n"
            f"[yellow]Expected Path:[/yellow] {full_path}\n\n"
            f"[dim]Please ensure the module file exists[/dim]",
            title="[bold red]File Not Found[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)

    # Dependency Check
    required_tools = MODULE_REQUIRED_TOOLS.get(module, [])
    missing_tools = []
    
    # Common Go bin path for security tools
    go_bin = Path.home() / "go" / "bin"
    
    for tool in required_tools:
        # Check standard PATH
        if shutil.which(tool):
            continue
        # Check Go bin
        if (go_bin / tool).exists():
            continue
        # Check Common local bin
        if (Path.home() / ".local" / "bin" / tool).exists():
            continue
            
        missing_tools.append(tool)

    if missing_tools:
        tools_list = "\n".join([f"  • [bold red]{t}[/bold red]" for t in missing_tools])
        error_panel = Panel(
            f"[bold red]✗ MISSING MODULE DEPENDENCIES[/bold red]\n\n"
            f"The module [cyan]{module}[/cyan] requires the following tools to be installed:\n\n"
            f"{tools_list}\n\n"
            f"[yellow]To fix, run:[/yellow] [bold cyan]hades --install[/bold cyan]\n"
            f"[dim]Note: Ensure Go tools are in your PATH (usually ~/go/bin)[/dim]",
            title="[bold red]Dependency Error[/bold red]",
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(1, 2)
        )
        console.print(error_panel)
        sys.exit(1)

    try:
        info_panel = Panel(
            f"[bold cyan]Executing Shell Module[/bold cyan]\n\n"
            f"[yellow]Module:[/yellow] {module}\n"
            f"[yellow]Script:[/yellow] {script_path}",
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(info_panel)
        console.print()

        result = subprocess.run(
            ["bash", str(full_path)],
            cwd=SCRIPT_DIR,
            check=False
        )

        if result.returncode == 0:
            success_panel = Panel(
                "[bold green]✓ Module Executed Successfully[/bold green]",
                border_style="green",
                box=box.ROUNDED
            )
            console.print()
            console.print(success_panel)
        else:
            error_panel = Panel(
                f"[bold red]✗ Module Execution Failed[/bold red]\n\n"
                f"[yellow]Exit Code:[/yellow] {result.returncode}",
                title="[bold red]Execution Error[/bold red]",
                border_style="red",
                box=box.ROUNDED
            )
            console.print()
            console.print(error_panel)
            sys.exit(result.returncode)

    except Exception as e:
        error_panel = Panel(
            f"[bold red]✗ Error Executing Module[/bold red]\n\n"
            f"[yellow]Error:[/yellow] {e}",
            title="[bold red]Fatal Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        console.print_exception()
        sys.exit(1)


# ============================================================================
# Web Interface
# ============================================================================

def start_web_interface() -> None:
    """Start the web-based HADES interface"""
    try:
        import uvicorn
        from hades.web.server import app, get_boot_diagnostics
        
        display_banner()
        
        # Get boot diagnostics
        boot_panel, frontend_exists = get_boot_diagnostics()

        ui_info = (
            "[bold white]HADES WEB DASHBOARD[/bold white]\n"
            "[dim]────────────────────────────────────[/dim]\n"
            "[bold green]▶  STATUS   :[/bold green] [bold white]ONLINE[/bold white]\n"
            "[bold cyan]🔗 URL      :[/bold cyan] [underline]http://localhost:9656[/underline]\n"
            "[bold blue]📖 API DOCS :[/bold blue] [underline]http://localhost:9656/docs[/underline]\n"
            "[dim]────────────────────────────────────[/dim]\n"
            "[dim yellow]💡 Action   : Press [bold]Ctrl+C[/bold] to stop[/dim yellow]"
        )
        
        info_panel = Panel(
            ui_info,
            title="[bold cyan]SYSTEM ENGINE[/bold cyan]",
            title_align="left",
            border_style="cyan",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
            expand=False
        )
        
        # Display side-by-side
        console.print(Columns([boot_panel, info_panel], padding=(0, 4)))
        console.print()

        # Critical warning if frontend is missing
        if not frontend_exists:
            console.print(
                f"  [bold red]⚠ UI ALERT:[/bold red] Dashboard files missing in [dim]frontend/dist[/dim]\n"
                "  [dim]To fix, run:[/dim] [bold cyan]cd frontend && npm install && npm run build[/bold cyan]\n"
            )

        uvicorn.run(app, host="0.0.0.0", port=9656, log_level="info")
    except ImportError:
        error_panel = Panel(
            "[bold red]HADES SYSTEM ENGINE ERROR[/bold red]\n"
            "[dim]────────────────────────────────────────────────[/dim]\n"
            "[bold red]▶  CAUSE    :[/bold red] [bold white]Missing Dependencies[/bold white]\n"
            "[bold yellow]📦 REQUIRE  :[/bold yellow] [bold white]fastapi, uvicorn[/bold white]\n\n"
            "[bold cyan]🛠️  FIX      :[/bold cyan] [underline]pip install fastapi uvicorn[/underline]\n"
            "[bold blue]🏗️  FRONTEND :[/bold blue] [underline]npm install && npm run build[/underline]\n"
            "[dim]────────────────────────────────────────────────[/dim]\n"
            "[dim yellow]💡 Action   : Install missing components and retry[/dim yellow]",
            title="[bold red]CRITICAL FAILURE[/bold red]",
            title_align="left",
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
            expand=False
        )
        console.print(error_panel)
        sys.exit(1)
    except Exception as e:
        error_panel = Panel(
            "[bold red]HADES SYSTEM ENGINE ERROR[/bold red]\n"
            "[dim]────────────────────────────────────────────────[/dim]\n"
            f"[bold red]▶  EXCEP    :[/bold red] [bold white]{e}[/bold white]\n"
            "[dim]────────────────────────────────────────────────[/dim]\n"
            "[dim yellow]💡 Action   : Check server logs for details[/dim yellow]",
            title="[bold red]RUNTIME FAILURE[/bold red]",
            title_align="left",
            border_style="red",
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
            expand=False
        )
        console.print(error_panel)
        sys.exit(1)


# ============================================================================
# Template Management
# ============================================================================

def handle_template_management(templates_arg: str) -> None:
    """Handle template management commands"""
    try:
        from hades.templates.manager import TemplateManager

        manager = TemplateManager()
        command = templates_arg.strip()
        command_lower = command.lower()

        if command_lower == "list":
            display_banner()
            manager.list_all()
        elif command_lower == "create":
            display_banner()
            manager.create_interactive()
        elif command_lower.startswith("edit"):
            parts = command.split(maxsplit=1)
            template_name = parts[1] if len(parts) > 1 else None
            display_banner()
            manager.edit_interactive(template_name)
        elif command_lower.startswith("delete"):
            parts = command.split(maxsplit=1)
            template_name = parts[1] if len(parts) > 1 else None
            display_banner()
            manager.delete_interactive(template_name)
        elif command_lower.startswith("show"):
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                template_name = parts[1]
                display_banner()
                manager.show(template_name)
            else:
                console.print("[red]Please specify template name: --templates show <name>[/red]")
        else:
            console.print(f"[yellow]Template name '{command}' provided without --target[/yellow]")
            console.print("[yellow]Available commands: list, create, edit, delete, show[/yellow]")
            console.print("[yellow]Or use with --target: python hades.py --target <url> --templates {template_name}[/yellow]")
            sys.exit(1)
    except ImportError:
        error_panel = Panel(
            "[bold red]Template Management Not Available[/bold red]\n\n"
            "Template management module could not be imported.",
            title="[bold red]Error[/bold red]",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Database Flush
# ============================================================================

def _handle_flush_db_interactive() -> None:
    """Interactive database flush with confirmation"""
    display_banner()

    warning_panel = Panel(
        "[bold red]⚠️  WARNING: DATABASE FLUSH[/bold red]\n\n"
        "This action will permanently delete all:\n"
        "  • Registered Users\n"
        "  • Username History\n"
        "  • Password Reset Tokens\n\n"
        "[bold yellow]This action CANNOT be undone.[/bold yellow]",
        title="[bold red]Critical Action[/bold red]",
        border_style="red",
        box=box.ROUNDED,
        padding=(1, 2)
    )
    console.print(warning_panel)
    console.print()

    if Confirm.ask("[bold red]Are you absolutely sure you want to flush the database?[/bold red]", default=False):
        console.print("\n[cyan]Flushing database...[/cyan]")
        if flush_database():
            success_panel = Panel(
                "[bold green]✓ Database Flushed Successfully[/bold green]\n\n"
                "All user data has been cleared. You can now register a new account.",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            console.print(success_panel)
        else:
            console.print("[bold red]✗ Failed to flush database. Check if it's currently in use.[/bold red]")
    else:
        console.print("[yellow]Action cancelled.[/yellow]")


# ============================================================================
# Argument Parsing
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    if '--setup-api' in sys.argv or '--configure-api' in sys.argv:
        return argparse.Namespace(
            target=None, instruction=None, run_name=None,
            non_interactive=False, module=[], show_help=False,
            setup_api=True, install_deps=False, docker_setup=False
        )

    if '--setup-notifications' in sys.argv or '--setup-telegram' in sys.argv:
        return argparse.Namespace(
            target=None, instruction=None, run_name=None,
            non_interactive=False, module=[], show_help=False,
            setup_api=False, install_deps=False, docker_setup=False,
            setup_notifications=True
        )

    if '--docker-setup' in sys.argv or '--check-docker' in sys.argv:
        return argparse.Namespace(
            target=None, instruction=None, run_name=None,
            non_interactive=False, module=[], show_help=False,
            setup_api=False, install_deps=False, docker_setup=True
        )

    if '-i' in sys.argv and '--install' not in sys.argv:
        i_index = sys.argv.index('-i')
        if i_index + 1 >= len(sys.argv) or sys.argv[i_index + 1].startswith('-'):
            return argparse.Namespace(
                target=None, instruction=None, run_name=None,
                non_interactive=False, module=[], show_help=False,
                setup_api=False, install_deps=True, docker_setup=False
            )

    if '--install' in sys.argv:
        return argparse.Namespace(
            target=None, instruction=None, run_name=None,
            non_interactive=False, module=[], show_help=False,
            setup_api=False, install_deps=True, docker_setup=False
        )

    if '-h' in sys.argv or '--help' in sys.argv:
        return argparse.Namespace(
            target=None, instruction=None, run_name=None,
            non_interactive=False, module=[], show_help=True,
            setup_api=False, install_deps=False, docker_setup=False
        )

    has_target = '-t' in sys.argv or '--target' in sys.argv

    parser = argparse.ArgumentParser(
        description="HADES - Advanced Security Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False
    )

    parser.add_argument('--setup-api', '--configure-api', action='store_true', dest='setup_api')
    parser.add_argument('-t', '--target', action='append', dest='target')
    parser.add_argument('--instruction', dest='instruction')
    parser.add_argument('--run-name', dest='run_name')
    parser.add_argument('--templates', dest='templates')
    parser.add_argument('--web', action='store_true', dest='web')
    parser.add_argument('-n', '--non-interactive', action='store_true', dest='non_interactive')
    parser.add_argument('--flush-db', action='store_true', dest='flush_db')
    parser.add_argument('--setup-notifications', '--setup-telegram', action='store_true', dest='setup_notifications')

    if not has_target:
        args, unknown = parser.parse_known_args()
        args.module = [m for m in unknown if m]
        args.show_help = False
        if not hasattr(args, 'setup_api'):    args.setup_api = False
        if not hasattr(args, 'install_deps'): args.install_deps = False
        if not hasattr(args, 'docker_setup'): args.docker_setup = False
        return args
    else:
        try:
            args = parser.parse_args()
            args.module = []
            args.show_help = False
            if not hasattr(args, 'setup_api'):    args.setup_api = False
            if not hasattr(args, 'install_deps'): args.install_deps = False
            if not hasattr(args, 'docker_setup'): args.docker_setup = False
            return args
        except SystemExit:
            return argparse.Namespace(
                target=None, instruction=None, run_name=None,
                non_interactive=False, module=[], show_help=True,
                setup_api=False, install_deps=False, docker_setup=False
            )


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    if '--setup-api' not in sys.argv and '--configure-api' not in sys.argv:
        load_env_file()

    args = parse_arguments()

    if hasattr(args, 'setup_api') and args.setup_api:
        setup_api_key_interactive()
        sys.exit(0)

    if hasattr(args, 'setup_notifications') and args.setup_notifications:
        setup_notifications_interactive()
        sys.exit(0)

    if hasattr(args, 'install_deps') and args.install_deps:
        install_dependencies_interactive()
        sys.exit(0)

    if hasattr(args, 'docker_setup') and args.docker_setup:
        display_docker_setup_guide()
        sys.exit(0)

    if hasattr(args, 'templates') and args.templates and not args.target:
        handle_template_management(args.templates)
        sys.exit(0)

    if hasattr(args, 'web') and args.web:
        start_web_interface()
        sys.exit(0)

    if hasattr(args, 'flush_db') and args.flush_db:
        _handle_flush_db_interactive()
        sys.exit(0)

    if args.show_help or (not args.target and not args.module):
        display_help()
        sys.exit(0)

    if args.target:
        if not check_ai_agent_mode_available():
            deps = check_ai_agent_dependencies()
            missing_deps = [dep for dep, installed in deps.items() if not installed]

            error_panel = Panel(
                "[bold red]✗ AI Agent Mode Dependencies Not Available[/bold red]\n\n"
                f"[yellow]Missing:[/yellow] {', '.join(missing_deps) if missing_deps else 'Unknown'}\n\n"
                "[cyan]To install dependencies, run:[/cyan]\n"
                "[bold]  hades --install[/bold]\n\n"
                "[dim]Or manually:[/dim]\n"
                "[dim]  pip install -r requirements.txt --break-system-packages[/dim]",
                title="[bold red]Missing Dependencies[/bold red]",
                border_style="red",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            console.print(error_panel)
            console.print()

            if Confirm.ask("[bold yellow]Would you like to install dependencies now?[/bold yellow]"):
                install_dependencies_interactive()
                if check_ai_agent_mode_available():
                    display_banner()
                    run_ai_agent_mode(args)
                else:
                    console.print("[red]Installation completed but dependencies still missing.[/red]")
                    sys.exit(1)
            else:
                if args.module:
                    display_banner()
                    for module in args.module:
                        run_shell_module_mode(module)
                else:
                    console.print("[red]No shell module specified. Use --help to see available modules.[/red]")
                    sys.exit(1)
        else:
            display_banner()
            run_ai_agent_mode(args)

    elif args.module:
        display_banner()
        for module in args.module:
            run_shell_module_mode(module)

    else:
        display_help()
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        traceback.print_exc()
        sys.exit(1)