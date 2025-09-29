#!/usr/bin/env python3
"""
Interactive Project Manager CLI Launcher.

This script properly sets up the Python path and launches the project manager CLI.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.interactive_pm_test import main  # noqa: E402

if __name__ == "__main__":
    main()
