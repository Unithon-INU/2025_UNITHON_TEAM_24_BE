import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# --- 👇 프로젝트 루트 경로를 Python 경로에 추가 ---
# alembic 명령어를 프로젝트 루트 디렉토리에서 실행한다고 가정
PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
print(f"Alembic env.py: Added {PROJECT_ROOT} to sys.path")
# --- 👆 ---

# --- 👇 DB 모델, Base, 설정 import ---
try:
    from app.db.base_class import Base # DB 모델들의 Base 클래스
    # autogenerate 를 위해 사용하는 모든 모델 import
    from app.db.models.user import User
    from app.db.models.route import DbTravelRoute
    from app.core.config import settings # 설정 import (DATABASE_URL 참조 위함)
except ImportError as e:
    print(f"Error importing application modules in alembic/env.py: {e}")
    print("Ensure alembic command is run from the project root directory.")
    sys.exit(1)
# --- 👆 ---


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- 👇 sqlalchemy.url 설정 (settings 객체 사용) ---
# alembic.ini의 설정보다 .env 파일의 DATABASE_URL을 우선 사용
if settings and settings.DATABASE_URL:
    print(f"Alembic using DATABASE_URL from settings: {settings.DATABASE_URL[:15]}...") # URL 일부만 로깅
    config.set_main_option('sqlalchemy.url', settings.DATABASE_URL)
else:
    # settings 객체 로드 실패 또는 DATABASE_URL 없는 경우 ini 파일 값 사용 (경고 표시)
    print("Warning: DATABASE_URL not found in settings, falling back to alembic.ini configuration.")
    # 이 경우 alembic.ini에 sqlalchemy.url이 설정되어 있어야 함
    if not config.get_main_option("sqlalchemy.url"):
         print("CRITICAL ERROR: sqlalchemy.url is not set in alembic.ini either!")
         sys.exit(1)
# --- 👆 ---


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# --- 👇 target_metadata 설정 (올바른 위치) ---
target_metadata = Base.metadata
# --- 👆 ---

# --- ❗ 아래 target_metadata = None 줄은 삭제! ---
# target_metadata = None # <--- 이 줄 삭제!


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # url = config.get_main_option("sqlalchemy.url") # 이미 위에서 설정됨
    context.configure(
        url=config.get_main_option("sqlalchemy.url"), # 설정된 URL 사용
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # config.get_section으로 ini 파일에서 DB 설정 읽어옴
    # sqlalchemy.url은 위에서 동적으로 설정했으므로 engine_from_config가 사용
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    print("Running migrations offline...")
    run_migrations_offline()
else:
    print("Running migrations online...")
    run_migrations_online()

print("Alembic env.py script finished.")