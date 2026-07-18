import yaml
import os
from pathlib import Path

def get_config():
    """Load configuration from config.yaml"""
    script_dir = Path(__file__).parent.parent
    config_file = script_dir / "config" / "config.yaml"
    
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        return {}

def get_hades_version():
    """Get HADES version from config.yaml"""
    config = get_config()
    # Priority: versioning.current_version -> framework.version -> default
    version = config.get('versioning', {}).get('current_version')
    if not version:
        version = config.get('framework', {}).get('version', '10.0')
    return version
