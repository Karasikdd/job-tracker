import os
from collections.abc import Iterator

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

load_dotenv()

test_url = os.environ["TEST_DATABASE_URL"]

if make_url(test_url).database != "jobtracker_test":
    raise RuntimeError(
        "Tests require the separate jobtracker_test database"
    )

os.environ["DATABASE_URL"] = test_url
os.environ["SECRET_KEY"] = (
    "test-only-key-012345678901234567890123456789"
)

from app.database import get_db
from app.main import app

test_engine = create_engine(test_url)


@pytest.fixture
def db_session() -> Iterator[Session]:
    with test_engine.connect() as connection:
        transaction = connection.begin()

        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as session:
                yield session
        finally:
            if transaction.is_active:
                transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_db() -> Iterator[Session]:
        yield db_session

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override