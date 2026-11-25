"""JSON 只用于导入；接口每次从数据库查询。"""
import json
from pathlib import Path

from backend.app.schemas import Place
from backend.app.models import Attraction
from sqlalchemy import select
from sqlalchemy.orm import Session

DATA_FILE = Path(__file__).resolve().parents[2] / 'data/demo/campus.json'


def load_places() -> tuple[Place, ...]:
    data = json.loads(DATA_FILE.read_text(encoding='utf-8'))
    if data.get('dataset_type') != 'course_demo':
        raise ValueError('阶段 1 仅支持 course_demo 数据集')
    places = tuple(Place.model_validate(item) for item in data['places'])
    if not places or len({p.id for p in places}) != len(places):
        raise ValueError('地点为空或编号重复，请先运行数据整理脚本')
    return places


def query_places(session: Session, keyword: str | None = None) -> list[Place]:
    # 当前数据量很小；统一使用 Python casefold 保持阶段 1 的搜索语义。
    rows = session.scalars(select(Attraction).order_by(Attraction.id)).all()
    term = (keyword or '').strip().casefold()
    return [Place.model_validate(row, from_attributes=True) for row in rows
            if not term or term in row.name.casefold() or term in row.code.casefold()]


def find_place(session: Session, place_id: int) -> Place | None:
    row = session.get(Attraction, place_id)
    return Place.model_validate(row, from_attributes=True) if row else None
