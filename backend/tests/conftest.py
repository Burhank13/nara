import os
from collections.abc import Iterator

import pytest
import sqlalchemy as sa

# The app reads its settings at import time, so the test database is chosen before anything else.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://nara:nara@localhost:5432/nara_test")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
# backend/.env holds a real Resend key for development. Blanking it here keeps the suite offline:
# without it, tests would post invites and reset links to the provider for every fake address.
os.environ["RESEND_API_KEY"] = ""

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _create_test_database() -> None:
    url = sa.engine.make_url(TEST_DATABASE_URL)
    maintenance = sa.create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with maintenance.connect() as connection:
        exists = connection.scalar(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        )
        if not exists:
            connection.execute(sa.text(f'CREATE DATABASE "{url.database}"'))
    maintenance.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[sa.Engine]:
    _create_test_database()

    config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    test_engine = sa.create_engine(TEST_DATABASE_URL)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: sa.Engine) -> Iterator[Session]:
    """Each test runs inside one transaction that is rolled back, so tests never see each other's rows."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
