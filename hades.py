#!/usr/bin/env python3
import sys
import logging
import warnings

# Silence noisy 3rd party warnings and logs
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("paramiko").setLevel(logging.ERROR)
logging.getLogger("numexpr").setLevel(logging.ERROR)

from pathlib import Path

# Explicitly add current directory to sys.path to ensure hades package is found
script_dir = Path(__file__).parent.absolute()
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from main import main

if __name__ == "__main__":
    main()
