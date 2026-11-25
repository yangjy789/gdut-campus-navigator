"""仅在未初始化的空库导入课程示例；导入记录与数据同一事务提交。"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database import make_engine
from backend.app.models import Attraction, Road, DataImport
from backend.app.repository import DATA_FILE, load_places
from scripts.prepare_demo import validate


def seed(engine):
    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    validate(data)
    places = load_places()
    added_places = added_roads = 0
    with Session(engine) as session, session.begin():
        if session.get(DataImport, 'course_demo_v1') is not None:
            return {'added_places': 0, 'added_roads': 0}
        session.add(DataImport(key='course_demo_v1'))
        # 对已有数据只登记初始化，不尝试填补管理员有意删除的 ID。
        if (session.scalar(select(Attraction.id).limit(1)) is not None
                or session.scalar(select(Road.id).limit(1)) is not None):
            return {'added_places': 0, 'added_roads': 0}
        for place in places:
            if session.get(Attraction, place.id) is None:
                session.add(Attraction(**place.model_dump()))
                added_places += 1
        session.flush()
        for road in data['roads']:
            if session.get(Road, road['id']) is None:
                road = dict(road)
                road['start_id'], road['end_id'] = sorted((road['start_id'], road['end_id']))
                session.add(Road(**road))
                added_roads += 1
    return {'added_places': added_places, 'added_roads': added_roads}


if __name__ == '__main__':
    engine = make_engine()
    try:
        print(seed(engine))
    finally:
        engine.dispose()
