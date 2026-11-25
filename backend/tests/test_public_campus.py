"""官方资料可以展示，但不能冒充已核验 GPS 数据或可通行路线。"""
import json

from backend.app.config import ROOT
from backend.app.public_campus import dataset
from backend.app.knowledge import KnowledgeIndex


def test_public_dataset_provenance_and_coordinates():
    data = dataset()
    assert data['dataset_type'] == 'official_public_reference'
    assert data['real_navigation_ready'] is False and data['roads'] == []
    assert data['coordinate_system'] == 'official_map_image_pixels'
    places = data['places']
    assert len(places) == len({p['id'] for p in places}) == 51
    assert sum(p['planned'] for p in places) == 1
    for p in places:
        assert p['latitude'] is None and p['longitude'] is None
        assert p['verification_status'] == 'official_document_only'
        assert p['source_url'].startswith('https://www.gdut.edu.cn/')
        assert 0 <= p['image_position']['x'] <= data['map']['width']
        assert 0 <= p['image_position']['y'] <= data['map']['height']
    assert next(p for p in places if p['id']=='shuren')['planned']


def test_public_endpoints_keep_demo_database_separate(client):
    response = client.get('/api/campus/real')
    assert response.status_code == 200
    assert response.json()['dataset_type'] == 'official_public_reference'
    assert client.get('/api/health').json()['place_count'] == 51
    assert client.get('/api/places').json()['dataset_type'] == 'course_demo'
    image = client.get('/api/campus/real/map')
    assert image.status_code == 200 and image.headers['content-type'] == 'image/png'
    assert image.content.startswith(b'\x89PNG\r\n\x1a\n')


def test_official_place_names_can_be_retrieved(tmp_path):
    index = KnowledgeIndex(tmp_path/'chroma')
    assert 'public-place-university-square' in {d['id'] for d in index.retrieve('工大广场原来叫什么？')}
    documents = json.loads((ROOT/'data/knowledge/campus.json').read_text(encoding='utf-8'))
    shuren = next(d for d in documents if d['id']=='public-place-shuren')
    assert '规划中' in shuren['content']
