"""阶段 7：AI 工具调用规划路线的隔离测试，不调用真实模型。"""
import json

import httpx
import pytest
from fastapi import HTTPException

from backend.app import qa, tool_assistant as ta
from backend.app.database import get_session
from backend.app.place_resolver import resolve_place, place_names
from backend.app.schemas import Place

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.models import Base
from scripts.seed_demo import seed


@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)

    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')

    Base.metadata.create_all(engine)
    seed(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def places(db):
    from sqlalchemy import select
    from backend.app.models import Attraction
    return [Place.model_validate(r, from_attributes=True)
            for r in db.scalars(select(Attraction).order_by(Attraction.id))]


def tool_response(start, end):
    args = json.dumps({'start_place': start, 'end_place': end}, ensure_ascii=False)
    return httpx.Response(200, json={'choices': [{'message': {
        'tool_calls': [{'function': {'name': 'plan_route', 'arguments': args}}]}}]})


def install(monkeypatch, response):
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs): return response
    monkeypatch.setattr(ta.httpx, 'Client', Client)
    monkeypatch.setattr(qa, 'settings', lambda: ('test-key-not-real', qa.MODEL))


# ---- 地点解析 ----

def test_resolve_aliases_exact_and_ambiguous(db):
    ps = places(db)
    assert resolve_place('北门', ps) == 0
    assert resolve_place('图书馆', ps) == 1
    assert resolve_place('食堂', ps) == 6
    assert resolve_place('DiningHall', ps) == 6
    assert resolve_place('DIN', ps) == 6
    assert resolve_place('从北门', ps) == 0          # 别名包含于短语
    assert resolve_place('不存在的地方', ps) is None
    assert resolve_place('教学楼', ps) is None       # TA/TB 歧义，不猜


@pytest.mark.parametrize('expr', ['图书馆或北门', '图书馆附近的咖啡店', '北门到图书馆', '教学楼'])
def test_partial_and_multiple_places_are_rejected(db, expr):
    assert resolve_place(expr, places(db)) is None


def test_renamed_place_drops_demo_alias_and_display_name(db):
    ps = places(db)
    ps[0] = ps[0].model_copy(update={'name': '新校医院'})
    assert resolve_place('北门', ps) is None
    assert resolve_place('新校医院', ps) == 0
    assert place_names(ps)[0] == '新校医院'


def test_duplicate_names_are_ambiguous(db):
    ps = places(db)
    ps[0] = ps[0].model_copy(update={'name': '新地点'})
    ps[1] = ps[1].model_copy(update={'name': '新地点'})
    assert resolve_place('新地点', ps) is None


def test_explicit_question_falls_back_when_model_omits_tool(monkeypatch, db):
    monkeypatch.setattr(ta, 'extract_places', lambda q, s: ('', ''))
    result = ta.plan_from_question('从北门到食堂怎么走？', db)
    assert result.status == 'planned' and result.route.distance_m == 290
    assert not result.tool_used and result.extraction_method == 'explicit_pattern'


def test_explicit_question_corrects_model_wrong_endpoint(monkeypatch, db):
    monkeypatch.setattr(ta, 'extract_places', lambda q, s: ('图书馆', '食堂'))
    result = ta.plan_from_question('从北门到食堂怎么走', db)
    assert result.route.start_id == 0
    assert result.extraction_method == 'explicit_pattern' and not result.tool_used


@pytest.mark.parametrize('question', ['从图书馆或北门到食堂', '从图书馆附近的咖啡店到食堂'])
def test_user_original_place_is_validated_before_model(monkeypatch, db, question):
    def forbidden(*args):
        pytest.fail('不明确的原文不应交给模型猜测地点')
    monkeypatch.setattr(ta, 'extract_places', forbidden)
    result = ta.plan_from_question(question, db)
    assert result.status == 'need_clarification' and result.route is None


# ---- 工具抽取 ----

def test_extract_returns_only_place_phrases(monkeypatch, db):
    install(monkeypatch, tool_response('北门', '食堂'))
    start, end = ta.extract_places('从北门到食堂怎么走', db)
    assert (start, end) == ('北门', '食堂')


def test_no_tool_call_returns_empty(monkeypatch, db):
    install(monkeypatch, httpx.Response(200, json={'choices': [{'message': {'content': '我不知道'}}]}))
    assert ta.extract_places('今天天气怎么样', db) == ('', '')


def test_wrong_tool_name_ignored(monkeypatch, db):
    r = httpx.Response(200, json={'choices': [{'message': {
        'tool_calls': [{'function': {'name': 'other_tool', 'arguments': '{}'}}]}}]})
    install(monkeypatch, r)
    assert ta.extract_places('从北门到食堂', db) == ('', '')


@pytest.mark.parametrize('status,expected', [(401,503),(403,503),(429,429),(503,503),(500,502)])
def test_provider_errors_sanitized(monkeypatch, db, status, expected):
    install(monkeypatch, httpx.Response(status, json={}))
    with pytest.raises(HTTPException) as e:
        ta.extract_places('从北门到食堂', db)
    assert e.value.status_code == expected
    assert 'test-key' not in e.value.detail


def test_missing_key_rejected(monkeypatch, db):
    monkeypatch.setattr(qa, 'settings', lambda: ('', qa.MODEL))
    with pytest.raises(HTTPException) as e:
        ta.extract_places('从北门到食堂', db)
    assert e.value.status_code == 503


# ---- 端到端规划（模型响应被替换，路线由真实算法计算）----

def test_plan_computes_real_route(monkeypatch, db):
    install(monkeypatch, tool_response('北门', '食堂'))
    result = ta.plan_from_question('从北门到食堂怎么走', db)
    assert result.status == 'planned' and result.tool_used is True
    assert result.route.start_id == 0 and result.route.end_id == 6
    assert result.route.algorithm == 'dijkstra'
    # 距离必须来自算法：校验每段距离之和等于总距离，且路径首末正确。
    assert result.route.distance_m == sum(s.distance_m for s in result.route.segments)
    assert result.route.path[0].id == 0 and result.route.path[-1].id == 6
    assert '示例' in result.message


def test_unrecognized_place_never_fabricates_route(monkeypatch, db):
    install(monkeypatch, tool_response('火星基地', '食堂'))
    result = ta.plan_from_question('从火星基地到食堂', db)
    assert result.status == 'need_clarification' and result.route is None


def test_ambiguous_place_never_fabricates_route(monkeypatch, db):
    install(monkeypatch, tool_response('教学楼', '食堂'))
    result = ta.plan_from_question('从教学楼到食堂', db)
    assert result.status == 'need_clarification' and result.route is None


def test_same_place_rejected(monkeypatch, db):
    install(monkeypatch, tool_response('北门', '北门'))
    result = ta.plan_from_question('从北门到北门', db)
    assert result.status == 'need_clarification' and result.route is None


def test_no_tool_call_is_clarification(monkeypatch, db):
    install(monkeypatch, httpx.Response(200, json={'choices': [{'message': {'content': ''}}]}))
    result = ta.plan_from_question('今天天气怎么样', db)
    assert result.status == 'need_clarification' and result.route is None


# ---- 接口层 ----

def test_endpoint_uses_real_session(monkeypatch, client):
    ta._calls.clear()
    monkeypatch.setattr(ta, 'extract_places', lambda q, s: ('北门', '食堂'))
    r = client.post('/api/assistant/route', json={'question': '从北门到食堂怎么走'})
    assert r.status_code == 200
    assert r.json()['status'] == 'planned'
    assert r.json()['route']['end_id'] == 6
    assert r.json()['route']['distance_m'] > 0
    ta._calls.clear()


def test_endpoint_validation_and_limit(monkeypatch, client):
    ta._calls.clear()
    monkeypatch.setattr(ta, 'plan_from_question', lambda q, s: ta.RoutePlanResult(status='need_clarification', message='说清楚地点'))
    assert client.post('/api/assistant/route', json={'question': ' '}).status_code == 422
    assert client.post('/api/assistant/route', json={'question': 'a' * 301}).status_code == 422
    for _ in range(10):
        assert client.post('/api/assistant/route', json={'question': '从北门到食堂'}).status_code == 200
    assert client.post('/api/assistant/route', json={'question': '从北门到食堂'}).status_code == 429
    ta._calls.clear()


def test_route_status_endpoint(client, monkeypatch):
    monkeypatch.setattr(qa, 'settings', lambda: ('test-key', qa.MODEL))
    r = client.get('/api/assistant/route/status')
    assert r.status_code == 200
    assert r.json()['tool'] == 'plan_route'
    assert r.json()['configured'] is True
