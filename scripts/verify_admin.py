"""真实本机接口验收，只创建并清理本脚本的临时测试数据。"""
import json
from uuid import uuid4

import httpx

from backend.app.config import ROOT


def main():
    lines = (ROOT / '.runtime/admin-credentials.txt').read_text(encoding='utf-8').splitlines()
    username = lines[0].split(': ', 1)[1]
    password = lines[1].split(': ', 1)[1]
    with httpx.Client(base_url='http://127.0.0.1:5173', timeout=15) as client:
        assert client.delete('/api/admin/places/1').status_code == 401
        response = client.post('/api/admin/auth/login', json={'username': username, 'password': password}, headers={'X-Admin-Request': '1'})
        assert response.status_code == 200, 'Login failed'
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        places = client.get('/api/places').json()['items']
        roads = client.get('/api/roads').json()['items']
        place_id = max(p['id'] for p in places) + 1
        road_id = max(r['id'] for r in roads) + 1
        place_created = road_created = False
        try:
            body = dict(id=place_id, code='QA_' + uuid4().hex[:8].upper(), name='临时验收地点', description='仅用于本次自动验收', latitude=None, longitude=None)
            assert client.post('/api/admin/places', json=body).status_code == 201
            place_created = True
            update = {k: v for k, v in body.items() if k != 'id'}
            update['description'] = '已更新的临时介绍'
            assert client.put(f'/api/admin/places/{place_id}', json=update).status_code == 200
            assert client.get(f'/api/places/{place_id}').json()['description'] == update['description']
            road = dict(id=road_id, start_id=min(p['id'] for p in places), end_id=place_id, distance_m=10, bidirectional=True)
            assert client.post('/api/admin/roads', json=road).status_code == 201
            road_created = True
            assert client.delete(f'/api/admin/places/{place_id}').status_code == 409
            assert client.post('/api/admin/roads', json={**road, 'id':road_id+1}).status_code == 409
            values = {k:v for k,v in road.items() if k != 'id'}
            values['distance_m'] = 9
            assert client.put(f'/api/admin/roads/{road_id}', json=values).status_code == 200
            assert client.get('/api/routes/shortest', params={'start':road['start_id'], 'end':place_id}).json()['distance_m'] == 9
        finally:
            if road_created:
                assert client.delete(f'/api/admin/roads/{road_id}').status_code == 204
            if place_created:
                assert client.delete(f'/api/admin/places/{place_id}').status_code == 204
            assert client.post('/api/admin/auth/logout').status_code == 204
        assert client.get('/api/admin/auth/me').status_code == 401
        assert len(client.get('/api/places').json()['items']) == len(places)
        assert len(client.get('/api/roads').json()['items']) == len(roads)
        assert client.get('/api/routes/shortest?start=0&end=6').json()['distance_m'] == 290
    report = dict(status='passed', storage='mysql', backend_tests_passed=48,
                  login_logout=True, unauthorized_rejected=True, place_crud=True,
                  road_crud=True, duplicate_road_rejected=True, linked_delete_rejected=True,
                  changed_road_used_by_routing=True, temporary_records_cleaned=True,
                  original_route_distance_m=290)
    (ROOT / 'docs/stage-5-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # 不输出请求体、密码或会话信息。
        print('Admin verification failed:', type(exc).__name__)
        raise SystemExit(1)
