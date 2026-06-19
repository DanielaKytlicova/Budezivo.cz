"""Pytest bootstrap: make backend modules importable regardless of the CWD.

Lets the suite run from either /app or /app/backend (the testing agent and CI
sometimes invoke pytest from the repo root, which otherwise breaks
`from routes import ...` / `from services import ...` imports).
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
