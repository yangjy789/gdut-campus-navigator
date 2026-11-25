"""仅用于测试/新建空表的校园目录初始化，不恢复删除的地点。"""
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models import CampusPlace, DataImport
from backend.app.public_campus import dataset


def seed_public(engine):
    with Session(engine) as session, session.begin():
        if session.get(DataImport, 'public_campus_2026_v1'):
            return
        if session.scalar(select(CampusPlace.id).limit(1)) is None:
            session.add_all(CampusPlace(id=p['id'],payload=p) for p in dataset()['places'])
        session.add(DataImport(key='public_campus_2026_v1'))
