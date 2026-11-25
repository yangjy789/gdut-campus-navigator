"""受认证与 CSRF 校验保护的地点和道路管理。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from backend.app.auth import DB, require_admin
from backend.app.models import Attraction, Road
from backend.app.schemas import Place, RoadInfo

router = APIRouter(prefix='/api/admin', tags=['管理员数据管理'], dependencies=[Depends(require_admin)])
ID = Annotated[int, Path(ge=0, le=2147483647)]


class PlaceBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    code: str = Field(min_length=1, max_length=16, pattern=r'^[A-Z][A-Z0-9_]*$')
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=5000)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @model_validator(mode='after')
    def paired_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError('经纬度必须一起填写或一起留空')
        return self


class NewPlace(PlaceBody):
    id: int = Field(ge=0, le=2147483647)


class RoadBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_id: int = Field(ge=0, le=2147483647)
    end_id: int = Field(ge=0, le=2147483647)
    distance_m: int = Field(gt=0, le=2147483647)
    bidirectional: bool = True

    @model_validator(mode='after')
    def ordered_endpoints(self):
        if self.start_id >= self.end_id:
            raise ValueError('起点编号必须小于终点编号；单向道路仅沿此方向通行')
        return self


class NewRoad(RoadBody):
    id: int = Field(ge=0, le=2147483647)


def commit(session):
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, '编号、代码或道路重复，或记录仍被其他数据引用')


def get_or_404(session, model, record_id):
    row = session.get(model, record_id)
    if row is None:
        raise HTTPException(404, '记录不存在')
    return row


@router.post('/places', response_model=Place, status_code=201)
def create_place(body: NewPlace, session: DB):
    row = Attraction(**body.model_dump(), verification_status='demo_only')
    session.add(row)
    commit(session)
    return Place.model_validate(row, from_attributes=True)


@router.put('/places/{record_id}', response_model=Place)
def update_place(record_id: ID, body: PlaceBody, session: DB):
    row = get_or_404(session, Attraction, record_id)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    commit(session)
    return Place.model_validate(row, from_attributes=True)


@router.delete('/places/{record_id}', status_code=204)
def delete_place(record_id: ID, session: DB):
    row = get_or_404(session, Attraction, record_id)
    if session.scalar(select(Road.id).where(or_(Road.start_id == record_id, Road.end_id == record_id)).limit(1)) is not None:
        raise HTTPException(409, '该地点仍连接道路，请先删除关联道路')
    session.delete(row)
    commit(session)
    return Response(status_code=204)


def check_endpoints(session, body):
    for record_id in (body.start_id, body.end_id):
        if session.get(Attraction, record_id) is None:
            raise HTTPException(422, '道路端点必须是已有地点')


@router.post('/roads', response_model=RoadInfo, status_code=201)
def create_road(body: NewRoad, session: DB):
    check_endpoints(session, body)
    row = Road(**body.model_dump(), verification_status='demo_only')
    session.add(row)
    commit(session)
    return RoadInfo.model_validate(row, from_attributes=True)


@router.put('/roads/{record_id}', response_model=RoadInfo)
def update_road(record_id: ID, body: RoadBody, session: DB):
    row = get_or_404(session, Road, record_id)
    check_endpoints(session, body)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    commit(session)
    return RoadInfo.model_validate(row, from_attributes=True)


@router.delete('/roads/{record_id}', status_code=204)
def delete_road(record_id: ID, session: DB):
    session.delete(get_or_404(session, Road, record_id))
    commit(session)
    return Response(status_code=204)
