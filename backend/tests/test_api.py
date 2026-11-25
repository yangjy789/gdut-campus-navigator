import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import Base
from scripts.seed_demo import seed
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


def test_health_and_catalog_label(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == dict(status='ok', dataset_type='campus_catalog', storage='database',
                                   place_count=51, real_navigation_ready=False)


def test_places_match_original_dataset(client):
    result = client.get('/api/places').json()
    assert result['total'] == 12
    assert len({p['id'] for p in result['items']}) == 12
    assert result['dataset_type'] == 'course_demo'
    assert all(p['latitude'] is None for p in result['items'])


@pytest.mark.parametrize('keyword', ['Library', 'lib', ' LIB '])
def test_search_name_code_and_whitespace(client, keyword):
    result = client.get('/api/places', params={'keyword': keyword}).json()
    assert result['total'] == 1
    assert result['items'][0]['code'] == 'LIB'


def test_search_no_match_and_empty(client):
    assert client.get('/api/places', params={'keyword': '不存在'}).json()['items'] == []
    assert client.get('/api/places', params={'keyword': '  '}).json()['total'] == 12


def test_detail_and_missing_place(client):
    response = client.get('/api/places/1')
    assert response.status_code == 200
    assert response.json()['name'] == 'Library'
    assert client.get('/api/places/999').status_code == 404


@pytest.mark.parametrize('path', ['/api/places/-1', '/api/places/abc',
                                   '/api/places?keyword=' + 'a' * 101])
def test_invalid_parameters(client, path):
    assert client.get(path).status_code == 422


def test_api_documentation(client):
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert '/api/places/{place_id}' in schema['paths']


def test_road_list_for_frontend(client):
    response = client.get('/api/roads')
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == len(data['items']) == 18
    assert data['real_navigation_ready'] is False
    assert all(r['distance_m'] > 0 and r['bidirectional'] for r in data['items'])


def test_shortest_route_and_reverse(client):
    response = client.get('/api/routes/shortest?start=0&end=6')
    assert response.status_code == 200
    route = response.json()
    assert route['distance_m'] == 290
    assert [p['id'] for p in route['path']] == [0, 1, 5, 6]
    assert [s['distance_m'] for s in route['segments']] == [120, 110, 60]
    assert route['real_navigation_ready'] is False
    reverse = client.get('/api/routes/shortest?start=6&end=0').json()
    assert reverse['distance_m'] == 290
    assert [(s['start_id'], s['end_id']) for s in reverse['segments']] == [(6, 5), (5, 1), (1, 0)]


def test_route_same_node_and_unknown(client):
    same = client.get('/api/routes/shortest?start=1&end=1').json()
    assert same['distance_m'] == 0 and same['segments'] == []
    assert [p['id'] for p in same['path']] == [1]
    assert client.get('/api/routes/shortest?start=999&end=1').status_code == 404
    assert client.get('/api/routes/shortest?start=1&end=999').status_code == 404


@pytest.mark.parametrize('query', ['start=-1&end=1', 'start=abc&end=1', 'start=1', 'end=1'])
def test_route_invalid_parameters(client, query):
    assert client.get('/api/routes/shortest?' + query).status_code == 422


def test_route_reads_database_changes_and_no_path(client):
    from sqlalchemy import delete
    from sqlalchemy.orm import Session
    from backend.app.models import Road
    # 仅修改隔离的 SQLite 测试库，验证每次规划都读取当前道路。
    with Session(app.state.engine) as session, session.begin():
        session.execute(delete(Road))
    response = client.get('/api/routes/shortest?start=0&end=6')
    assert response.status_code == 404
    assert response.json()['detail'] == '两点之间没有可通行路线'
