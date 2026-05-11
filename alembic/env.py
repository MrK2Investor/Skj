import os
import sys
from logging.config import fileConfig


from sqlalchemy import engine_from_config, pool
from alembic import context

# Přidání kořenové složky projektu do Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base

# Důležité: import všech modelů, aby je Alembic viděl
from app.models.file_model import FileModel
from app.models.bucket_model import BucketModel
from app.models.queued_message_model import QueuedMessageModel

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic bude porovnávat DB podle metadata z Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()