from urllib.parse import urlparse,parse_qs
import pytest
from sqlalchemy.orm import Session
from backend.app.main import app
from backend.app.models import AdminUser, CampusPlace
from backend.app.auth import hash_password
from backend.app.campus_service import live_sources
from scripts.seed_public_campus import seed_public


def test_navigation_uses_real_catalog_names_and_no_invented_distance(client):
    r=client.post('/api/campus/real/route',json={'start_id':'south-gate','end_id':'library'})
    assert r.status_code==200
    data=r.json();url=urlparse(data['navigation_url']);args=parse_qs(url.query)
    assert url.scheme=='https' and url.netloc=='api.map.baidu.com'
    assert args['mode']==['walking'] and args['region']==['广州市']
    assert args['origin']==['广东工业大学大学城校区南门']
    assert args['destination']==['广东工业大学大学城校区图书馆']
    assert data['distance_m'] is None and 'route' not in data


@pytest.mark.parametrize('start,end,expected',[('south-gate','south-gate',422),('shuren','library',422),('unknown','library',404)])
def test_navigation_rejects_invalid_endpoints(client,start,end,expected):
    assert client.post('/api/campus/real/route',json={'start_id':start,'end_id':end}).status_code==expected


def test_plain_question_and_ambiguous_target(client):
    r=client.post('/api/campus/real/assistant/route',json={'question':'从南门到图书馆怎么走？'})
    assert r.status_code==200 and r.json()['status']=='navigation_ready'
    assert r.json()['extraction_method']=='explicit_pattern'
    for question in ['从南门到图书馆附近咖啡店','从南门到新科技大楼']:
        r=client.post('/api/campus/real/assistant/route',json={'question':question})
        assert r.status_code==200 and r.json()['status']=='need_clarification'


def test_admin_catalog_auth_csrf_and_shared_crud(client):
    body={'id':'test-campus-place','name':'统一目录测试地点','region':'教学区','category':'服务','aliases':['测试别名'],
          'image_position':{'x':10,'y':20},'description':'用于隔离测试','planned':False,
          'source_url':'https://www.gdut.edu.cn/','source_document_url':'https://www.gdut.edu.cn/','checked_on':'2026-11-24'}
    assert client.post('/api/admin/campus/places',json=body).status_code==401
    with Session(app.state.engine) as s,s.begin():
        s.add(AdminUser(username='catalog-admin',password_hash=hash_password('test-only-password'),active=True))
    login=client.post('/api/admin/auth/login',json={'username':'catalog-admin','password':'test-only-password'},headers={'X-Admin-Request':'1'})
    assert login.status_code==200
    assert client.post('/api/admin/campus/places',json=body).status_code==403
    headers={'X-CSRF-Token':login.json()['csrf_token']}
    assert client.post('/api/admin/campus/places',json=body,headers=headers).status_code==201
    assert client.get('/api/health').json()['place_count']==52
    body.pop('id');body['name']='更新后的校园地点'
    assert client.put('/api/admin/campus/places/test-campus-place',json=body,headers=headers).status_code==200
    with Session(app.state.engine) as s:
        sources=live_sources('更新后的校园地点在哪里？',s)
        assert any(d['title']=='更新后的校园地点地点资料' for d in sources)
        assert not any('统一目录测试地点' in d['title'] for d in sources)
    assert client.delete('/api/admin/campus/places/test-campus-place',headers=headers).status_code==204
    seed_public(app.state.engine)
    assert client.get('/api/health').json()['place_count']==51
    with Session(app.state.engine) as s:
        assert s.get(CampusPlace,'test-campus-place') is None


def test_admin_coordinates_and_urls_are_validated(client):
    # 请求体校验与身份验证各自独立；模型层直接校验阻止恶意链接和伪坐标。
    from backend.app.campus_admin import PlaceBody
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PlaceBody(name='x',region='教学区',category='学习',image_position={'x':1400,'y':-1},source_url='javascript:alert(1)',source_document_url='https://www.gdut.edu.cn/',checked_on='2026-11-24')
