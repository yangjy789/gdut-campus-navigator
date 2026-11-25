"""只读官方校园资料，与课设数据库和示例路线严格分开。"""
import json
from copy import deepcopy
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.database import get_session
from backend.app.models import CampusPlace

from backend.app.config import ROOT

DIRECTORY = ROOT / 'data/public_campus'
router = APIRouter(prefix='/api/campus/real', tags=['官网真实校园资料'])


@lru_cache(maxsize=1)
def dataset():
    data = json.loads((DIRECTORY/'campus.json').read_text(encoding='utf-8'))
    if data['dataset_type'] != 'official_public_reference' or data['real_navigation_ready']:
        raise ValueError('官方资料数据集状态异常')
    return data


def catalog(session: Session):
    data = deepcopy(dataset())
    data['places'] = [row.payload for row in session.scalars(select(CampusPlace).order_by(CampusPlace.id))]
    return data


@router.get('')
def public_campus(session: Annotated[Session, Depends(get_session)]):
    return catalog(session)


@router.get('/map', response_class=FileResponse)
def public_map():
    return FileResponse(DIRECTORY/'official-map.png', media_type='image/png',
                        headers={'Cache-Control':'public, max-age=3600'})
