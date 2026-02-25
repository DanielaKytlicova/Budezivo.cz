"""
Budeživo.cz - Cultural Booking SaaS Backend
Legacy entry point - redirects to main.py

This file maintains backwards compatibility with existing deployment.
The actual application is now in main.py with modular architecture.
"""

# Import and re-export the app from the new modular structure
from main import app

# This allows uvicorn to run with: uvicorn server:app
# while the actual code lives in the modular main.py
