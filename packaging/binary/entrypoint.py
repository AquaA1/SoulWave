#!/usr/bin/env python3
"""Standalone entrypoint for Soulwave PyInstaller binary."""
import sys
from pathlib import Path

# Ensure repo root / package parent directory is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from soulwave.cli import main

if __name__ == "__main__":
    main()
