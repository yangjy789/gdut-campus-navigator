from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth import COOKIE, hash_password, now, token_hash, verify_password
from backend.app.main import app
from backend.app.models import AdminSession, AdminUser

TEST_PASSWORD = 'Only-for-isolated-tests!'


@pytest.fixture
def account(client):
    with Session(app.state.engine) as session, session.begin():
        session.add(AdminUser(username='tester', password_hash=hash_password(TEST_PASSWORD), active=True))
    return client


def login(client):
    result = client.post('/api/admin/auth/login', json={'username': 'tester', 'password': TEST_PASSWORD}, headers={'X-Admin-Request': '1'})
    assert result.status_code == 200
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    return result


def test_password_hash_and_verify():
    first, second = hash_password(TEST_PASSWORD), hash_password(TEST_PASSWORD)
    assert first != second and TEST_PASSWORD not in first
    assert verify_password(TEST_PASSWORD, first)
    assert not verify_password('wrong', first)


def test_login_cookie_logout_and_revocation(account):
    response = login(account)
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie and 'path=/api/admin' in cookie
    token = account.cookies.get(COOKIE)
    with Session(app.state.engine) as session:
        assert session.get(AdminSession, token_hash(token)) is not None
    assert account.get('/api/admin/auth/me').json()['username'] == 'tester'
    assert account.post('/api/admin/auth/logout').status_code == 204
    account.cookies.set(COOKIE, token, path='/api/admin')
    assert account.get('/api/admin/auth/me').status_code == 401


def test_wrong_password_rate_limit_and_header(account):
    body = {'username': 'tester', 'password': 'wrong'}
    assert account.post('/api/admin/auth/login', json=body).status_code == 403
    for _ in range(10):
        assert account.post('/api/admin/auth/login', json=body, headers={'X-Admin-Request': '1'}).status_code == 401
    assert account.post('/api/admin/auth/login', json=body, headers={'X-Admin-Request': '1'}).status_code == 429


def test_expired_and_disabled_account(account):
    login(account)
    with Session(app.state.engine) as session, session.begin():
        record = session.scalar(select(AdminSession))
        record.expires_at = now() - timedelta(seconds=1)
    assert account.get('/api/admin/auth/me').status_code == 401
    login(account)
    with Session(app.state.engine) as session, session.begin():
        session.scalar(select(AdminUser)).active = False
    assert account.get('/api/admin/auth/me').status_code == 401


@pytest.mark.parametrize('method,path', [('post', '/api/admin/places'), ('put', '/api/admin/places/1'),
    ('delete', '/api/admin/places/1'), ('post', '/api/admin/roads'), ('put', '/api/admin/roads/1'), ('delete', '/api/admin/roads/1')])
def test_all_writes_require_login(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_csrf_and_origin(account):
    login(account)
    saved = account.headers.pop('X-CSRF-Token')
    assert account.delete('/api/admin/places/1').status_code == 403
    account.headers['X-CSRF-Token'] = saved
    assert account.delete('/api/admin/places/1', headers={'Origin': 'https://evil.example'}).status_code == 403
    assert account.post('/api/admin/auth/login', json={'username': 'tester', 'password': TEST_PASSWORD},
                        headers={'X-Admin-Request': '1', 'Origin': 'https://evil.example'}).status_code == 403


def test_place_crud_conflicts_and_linked_delete(account):
    login(account)
    body = dict(id=50, code='TEST', name='测试地点', description='介绍', latitude=None, longitude=None)
    assert account.post('/api/admin/places', json=body).status_code == 201
    assert account.post('/api/admin/places', json=body).status_code == 409
    body.pop('id')
    body['description'] = '已修改'
    assert account.put('/api/admin/places/50', json=body).status_code == 200
    assert account.get('/api/places/50').json()['description'] == '已修改'
    assert account.delete('/api/admin/places/1').status_code == 409
    assert account.delete('/api/admin/places/50').status_code == 204
    assert account.delete('/api/admin/places/50').status_code == 404


def test_road_crud_changes_route(account):
    login(account)
    body = dict(id=50, start_id=0, end_id=6, distance_m=10, bidirectional=True)
    assert account.post('/api/admin/roads', json=body).status_code == 201
    assert account.get('/api/routes/shortest?start=0&end=6').json()['distance_m'] == 10
    assert account.post('/api/admin/roads', json={**body, 'id': 51}).status_code == 409
    body.pop('id')
    body['distance_m'] = 20
    assert account.put('/api/admin/roads/50', json=body).status_code == 200
    assert account.delete('/api/admin/roads/50').status_code == 204
    assert account.get('/api/routes/shortest?start=0&end=6').json()['distance_m'] == 290


@pytest.mark.parametrize('changes', [dict(distance_m=0), dict(start_id=999, end_id=1000),
                                    dict(start_id=1, end_id=1), dict(start_id=6, end_id=0)])
def test_road_validation(account, changes):
    login(account)
    body = dict(id=50, start_id=0, end_id=6, distance_m=10, bidirectional=True)
    assert account.post('/api/admin/roads', json={**body, **changes}).status_code == 422


def test_place_validation_and_missing_update(account):
    login(account)
    body = dict(code='TEST', name='   ', description='demo')
    assert account.post('/api/admin/places', json={**body, 'id': 50}).status_code == 422
    body['name'] = 'Test'
    assert account.post('/api/admin/places', json={**body, 'id': 50, 'latitude': 20}).status_code == 422
    assert account.put('/api/admin/places/999', json=body).status_code == 404
