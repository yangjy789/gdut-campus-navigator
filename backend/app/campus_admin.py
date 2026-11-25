"""受现有管理员认证与 CSRF 保护的统一校园目录。"""
from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from backend.app.auth import DB, require_admin
from backend.app.models import CampusPlace
from backend.app.admin import commit
from backend.app.public_campus import catalog

router=APIRouter(prefix='/api/admin/campus',tags=['校园目录管理'],dependencies=[Depends(require_admin)])
Name=Annotated[str,Field(min_length=1,max_length=100)]


class Position(BaseModel):
    model_config=ConfigDict(extra='forbid')
    x: int=Field(ge=0,le=1317)
    y: int=Field(ge=0,le=2000)


class PlaceBody(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    name: Name
    region: Annotated[str,Field(pattern='^(教学区|生活东区|生活西区)$')]
    category: Name
    aliases: list[Name]=Field(default_factory=list,max_length=20)
    planned: bool=False
    description: str=Field(default='',max_length=3000)
    image_position: Position
    source_url: HttpUrl
    source_document_url: HttpUrl
    checked_on: date


class NewPlace(PlaceBody):
    id: str=Field(min_length=1,max_length=64,pattern='^[a-z][a-z0-9-]*$')


def payload(body, record_id):
    return {**body.model_dump(mode='json',exclude={'id'}),'id':record_id,
            'latitude':None,'longitude':None,'verification_status':'editor_updated','source_page':1}


@router.get('/places')
def list_places(session: DB):
    return {'items':catalog(session)['places']}


@router.post('/places',status_code=201)
def create_place(body: NewPlace,session: DB):
    row=CampusPlace(id=body.id,payload=payload(body,body.id))
    session.add(row);commit(session)
    return row.payload


@router.put('/places/{record_id}')
def update_place(record_id: str,body: PlaceBody,session: DB):
    row=session.get(CampusPlace,record_id)
    if not row: raise HTTPException(404,'地点不存在')
    row.payload=payload(body,record_id);commit(session)
    return row.payload


@router.delete('/places/{record_id}',status_code=204)
def delete_place(record_id: str,session: DB):
    row=session.get(CampusPlace,record_id)
    if not row: raise HTTPException(404,'地点不存在')
    session.delete(row);commit(session)
    return Response(status_code=204)
