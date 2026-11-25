"""真实 MySQL 验收：重新连接、校验导入数量及约束，并记录无敏感信息报告。"""
import json
import re

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.app.config import ROOT
from backend.app.database import make_engine
from backend.app.models import Attraction, Road
from backend.app.repository import query_places
from scripts.seed_demo import seed


def main():
    engine = make_engine()
    try:
        with engine.connect() as connection:
            version = connection.scalar(text('SELECT VERSION()'))
            parts = tuple(int(n) for n in re.match(r'(\d+)\.(\d+)\.(\d+)', version).groups())
            if 'mariadb' in version.lower() or parts < (8, 0, 16):
                raise RuntimeError('本项目当前验收要求 MySQL >= 8.0.16')
        assert seed(engine) == {'added_places': 0, 'added_roads': 0}, '请先导入示例数据'
        engine.dispose()
        with Session(engine) as session:
            place_count = session.scalar(select(func.count()).select_from(Attraction))
            road_count = session.scalar(select(func.count()).select_from(Road))
            assert (place_count, road_count) == (12, 18)
            assert [p.code for p in query_places(session, 'lib')] == ['LIB']
        # 故意写入负距离，要求数据库拒绝；使用事务确保不留下测试数据。
        rejected = False
        with Session(engine) as session:
            transaction = session.begin()
            try:
                session.add(Road(id=1000000, start_id=0, end_id=2, distance_m=-1,
                                 bidirectional=True, verification_status='demo_only'))
                session.flush()
            except DBAPIError as exc:
                # MySQL/PyMySQL 将 CHECK 失败归为 OperationalError (3819)。
                # 必须确认具体错误码，不能把连接错误或主键冲突当作通过。
                if getattr(exc.orig, 'args', [None])[0] != 3819:
                    raise
                rejected = True
            finally:
                transaction.rollback()
        assert rejected, '数据库没有拒绝负距离'
        report = dict(storage='mysql', server_version=version,
                      place_count=place_count, road_count=road_count,
                      reconnect_read=True, seed_idempotent=True,
                      negative_distance_rejected=True, status='passed')
        (ROOT / 'docs/stage-2-check.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
