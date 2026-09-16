import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

load_dotenv()
test_url = os.environ["TEST_DATABASE_URL"]
if make_url(test_url).database != "jobtracker_test":
    raise RuntimeError("Tests require the separate jobtracker_test database")

os.environ["DATABASE_URL"] = test_url
os.environ["SECRET_KEY"] = "test-only-key-012345678901234567890123456789"

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_engine(test_url)


@pytest.fixture
def client():
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
                expire_on_commit=False,
            ) as session:
                def override_db():
                    yield session

                app.dependency_overrides[get_db] = override_db
                try:
                    with TestClient(app) as test_client:
                        yield test_client
                finally:
                    app.dependency_overrides.clear()
        finally:
            transaction.rollback()