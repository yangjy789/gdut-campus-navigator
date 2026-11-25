from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config import database_url


def make_engine():
    return create_engine(database_url(), pool_pre_ping=True,
                         connect_args={'connect_timeout': 5})


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session
