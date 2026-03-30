from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so autogenerate can detect them
from app.models.factory import Factory
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.location import Location
from app.models.gate_event import GateEvent
from app.models.alert import Alert
from app.database import Base

target_metadata = Base.metadata

# Use sync psycopg2 driver for Alembic (not asyncpg)
def get_url():
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    return url.replace("+asyncpg", "")


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
