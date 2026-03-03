"""
Alembic environment configuration for Supabase migrations.
"""
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Import models for autogenerate support
from database.models import Base

# this is the Alembic Config object
config = context.config

# Get DATABASE_URL from environment (sync version for Alembic)
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    config.set_main_option('sqlalchemy.url', DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# Resend .env soubor
RESEND_API_KEY=re_your_api_key_here
SENDER_EMAIL=noreply@budezivo.cz