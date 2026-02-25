"""
Application configuration loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')
MONGO_URL = os.environ.get('MONGO_URL')
DB_NAME = os.environ.get('DB_NAME')

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'change_this_secret_key')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 30  # 30 days

# Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# CORS
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')

# Package prices
PACKAGE_PRICES = {
    "basic": {"monthly": 990.0, "yearly": 9900.0},
    "standard": {"monthly": 1990.0, "yearly": 19900.0},
    "premium": {"monthly": 3990.0, "yearly": 39900.0}
}
