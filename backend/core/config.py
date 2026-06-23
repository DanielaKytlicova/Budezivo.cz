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
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET environment variable is required")
JWT_ALGORITHM = "HS256"

# Stripe
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')

# CORS
# CORS — SECURITY (audit P1 #6): a literal "*" origin combined with
# allow_credentials=True makes Starlette reflect ANY Origin and return
# Access-Control-Allow-Credentials: true, allowing any website to issue
# cookie-authenticated cross-site requests. We therefore HARD-STRIP "*" and
# only ever allow an explicit allowlist.
_cors_env = os.environ.get('CORS_ORIGINS', '')
_env_origins = [o.strip() for o in _cors_env.split(',') if o.strip() and o.strip() != '*']
CORS_ORIGINS = [
    "https://www.budezivo.cz",
    "https://budezivo.cz",
] + _env_origins

# In preview/dev, allow the preview domain
_react_url = os.environ.get('REACT_APP_BACKEND_URL', '')
if _react_url and _react_url not in CORS_ORIGINS:
    CORS_ORIGINS.append(_react_url)

# De-duplicate while preserving order, and never allow a bare wildcard.
CORS_ORIGINS = [o for i, o in enumerate(CORS_ORIGINS) if o != '*' and o not in CORS_ORIGINS[:i]]

# Frontend URL (for password reset links etc.)
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://www.budezivo.cz')

# Package prices
PACKAGE_PRICES = {
    "basic": {"monthly": 990.0, "yearly": 9900.0},
    "standard": {"monthly": 1990.0, "yearly": 19900.0},
    "premium": {"monthly": 3990.0, "yearly": 39900.0}
}
