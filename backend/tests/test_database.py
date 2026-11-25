import pytest
from sqlalchemy import create_engine, event, func, select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import Attraction, Base, Road, DataImport
from scripts.seed_demo import seed


@pytest.fixture
def engine(tmp_path):
    engine = create_engine('sqlite:///' + (tmp_path / 'test.db').as_posix())

    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_import_counts_idempotence_and_no_overwrite(engine):
    assert seed(engine) == {'added_places': 12, 'added_roads': 18}
    with Session(engine) as session, session.begin():
        session.get(Attraction, 1).description = '已核对的测试介绍'
    assert seed(engine) == {'added_places': 0, 'added_roads': 0}
    # 释放连接后重新读取文件数据库，验证实际持久化。
    engine.dispose()
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Attraction)) == 12
        assert session.scalar(select(func.count()).select_from(Road)) == 18
        assert session.get(Attraction, 1).description == '已核对的测试介绍'


def test_restart_does_not_restore_deleted_roads_or_places(engine):
    seed(engine)
    with Session(engine) as session, session.begin():
        session.execute(delete(Road).where((Road.start_id == 0) | (Road.end_id == 0)))
        session.execute(delete(Attraction).where(Attraction.id == 0))
    assert seed(engine) == {'added_places': 0, 'added_roads': 0}
    with Session(engine) as session:
        assert session.get(Attraction, 0) is None
        assert session.scalar(select(func.count()).select_from(Road)) < 18


def test_restart_preserves_intentionally_empty_dataset(engine):
    seed(engine)
    with Session(engine) as session, session.begin():
        session.execute(delete(Road))
        session.execute(delete(Attraction))
    assert seed(engine) == {'added_places': 0, 'added_roads': 0}
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Attraction)) == 0


def test_existing_install_is_marked_without_filling_missing_ids(engine):
    seed(engine)
    with Session(engine) as session, session.begin():
        session.execute(delete(DataImport))
        session.execute(delete(Road).where(Road.id == 0))
    assert seed(engine) == {'added_places': 0, 'added_roads': 0}
    with Session(engine) as session:
        assert session.get(Road, 0) is None
        assert session.get(DataImport, 'course_demo_v1') is not None


@pytest.mark.parametrize('changes', [dict(distance_m=-1), dict(end_id=999),
                                      dict(start_id=1, end_id=1)])
def test_road_constraints_and_transaction_rollback(engine, changes):
    seed(engine)
    with pytest.raises(IntegrityError):
        with Session(engine) as session, session.begin():
            session.get(Attraction, 1).name = '不应被提交'
            values = dict(id=100, start_id=0, end_id=2, distance_m=100,
                          bidirectional=True, verification_status='demo_only')
            values.update(changes)
            session.add(Road(**values))
    with Session(engine) as session:
        assert session.get(Attraction, 1).name == 'Library'
        assert session.get(Road, 100) is None
