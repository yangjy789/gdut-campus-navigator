import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.models import Base
from scripts.seed_demo import seed
from scripts.seed_public_campus import seed_public


@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)

    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    Base.metadata.create_all(engine)
    seed(engine)
    seed_public(engine)
    monkeypatch.setattr('backend.app.main.make_engine', lambda: engine)
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()
