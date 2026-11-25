"""从项目根目录启动：python -m uvicorn backend.app.main:app --reload"""
from contextlib import asynccontextmanager
from threading import Lock
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.database import get_session, make_engine
from backend.app.models import Attraction, Road, CampusPlace
from backend.app.repository import find_place, query_places
from backend.app.schemas import Place, PlaceList, ShortestRoute, RoadInfo, RoadList
from backend.app.route_service import plan_route
from backend.app.auth import router as auth_router
from backend.app.admin import router as admin_router
from backend.app.qa import router as qa_router
from backend.app.tool_assistant import router as tool_router
from backend.app.public_campus import router as public_campus_router
from backend.app.campus_service import router as campus_service_router
from backend.app.campus_admin import router as campus_admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.login_failures = {}
    app.state.login_lock = Lock()
    app.state.engine = make_engine()
    try:
        with app.state.engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        yield
    finally:
        app.state.engine.dispose()


app = FastAPI(
    title='广工 AI 校园导览 API',
    version='1.0.0',
    description='校园目录、地图探索、智能问答、步行地图衔接与认证管理；另提供独立路网算法接口。',
    lifespan=lifespan,
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(qa_router)
app.include_router(tool_router)
app.include_router(public_campus_router)
app.include_router(campus_service_router)
app.include_router(campus_admin_router)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    # 不把连接串、SQL 或数据库内部信息返回给浏览器。
    return JSONResponse(status_code=503, content={'detail': '数据库暂不可用，请检查连接和迁移状态'})


@app.get('/', tags=['服务信息'])
def index():
    return {'name': app.title, 'docs': '/docs', 'dataset_type': 'campus_catalog'}


@app.get('/api/health', tags=['服务信息'])
def health(session: Annotated[Session, Depends(get_session)]):
    count = session.scalar(select(func.count()).select_from(CampusPlace))
    return {'status': 'ok', 'dataset_type': 'campus_catalog',
            'storage': 'database', 'place_count': count,
            'real_navigation_ready': False}


@app.get('/api/places', response_model=PlaceList, tags=['地点查询'])
def list_places(
    session: Annotated[Session, Depends(get_session)],
    keyword: Annotated[str | None, Query(max_length=100, description='按名称或代码搜索，忽略大小写')] = None,
):
    places = query_places(session, keyword)
    return PlaceList(total=len(places), items=list(places))


@app.get('/api/places/{place_id}', response_model=Place, tags=['地点查询'])
def get_place(session: Annotated[Session, Depends(get_session)], place_id: Annotated[int, Path(ge=0)]):
    place = find_place(session, place_id)
    if place is not None:
        return place
    raise HTTPException(status_code=404, detail='地点不存在')


@app.get('/api/roads', response_model=RoadList, tags=['道路查询'])
def list_roads(session: Annotated[Session, Depends(get_session)]):
    roads = session.scalars(select(Road).order_by(Road.id)).all()
    return RoadList(total=len(roads), items=[RoadInfo.model_validate(row, from_attributes=True) for row in roads])


@app.get('/api/routes/shortest', response_model=ShortestRoute, tags=['路线规划'],
         responses={404: {'description': '起终点不存在，或两点之间没有可通行路线'}})
def get_shortest_route(
    session: Annotated[Session, Depends(get_session)],
    start: Annotated[int, Query(ge=0, description='起点编号，例如 0（NorthGate）')],
    end: Annotated[int, Query(ge=0, description='终点编号，例如 6（DiningHall）')],
):
    try:
        route = plan_route(session, start, end)
    except KeyError:
        raise HTTPException(status_code=404, detail='起点或终点不存在')
    except ValueError:
        raise HTTPException(status_code=503, detail='道路数据异常，暂时无法规划路线')
    if route is None:
        raise HTTPException(status_code=404, detail='两点之间没有可通行路线')
    return route
