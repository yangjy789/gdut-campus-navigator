import json

import httpx
import pytest
from fastapi import HTTPException

from backend.app import qa
from backend.app.knowledge import KnowledgeIndex, vector


@pytest.fixture
def index(tmp_path):
    return KnowledgeIndex(tmp_path / 'chroma')


def test_retrieval_official_project_and_unknown(index):
    assert index.retrieve('大学城校区的地址是什么？')[0]['id'] == 'campus-address'
    assert 'campus-map' in [s['id'] for s in index.retrieve('官方校园地图在哪里查看？')]
    assert 'project-demo' in [s['id'] for s in index.retrieve('示意图能用于真实导航吗？')]
    assert index.retrieve('量子纠缠实验设计') == []
    assert len(vector('图书馆')) == 1024
    assert vector('图书馆') == vector('图书馆')


def test_no_match_never_calls_provider(index, monkeypatch):
    monkeypatch.setattr(qa, 'get_index', lambda: index)
    monkeypatch.setattr(qa, 'generate', lambda *_: pytest.fail('Should not call model'))
    result = qa.answer_question('量子纠缠实验设计')
    assert result.status == 'insufficient_evidence' and result.model is None and not result.sources


def install_response(monkeypatch, status=200, content=None, error=None):
    captured = {}
    class Client:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            captured.update(url=url, **kwargs)
            return httpx.Response(status, json={'choices':[{'message':{'content':json.dumps(content)}}], 'error':error or {}})
    monkeypatch.setattr(qa.httpx, 'Client', Client)
    monkeypatch.setattr(qa, 'settings', lambda: ('test-secret-not-real', qa.MODEL))
    monkeypatch.setattr(qa, 'sleep', lambda _: None)
    return captured


def test_grounded_answer_and_sources(index, monkeypatch):
    monkeypatch.setattr(qa, 'get_index', lambda: index)
    captured = install_response(monkeypatch, content={'status':'answered','answer':'大学城外环西路100号 [campus-address]','source_ids':['campus-address']})
    result = qa.answer_question('大学城校区的地址是什么？')
    assert result.sources[0].source_type == 'official'
    assert result.sources[0].source_url.startswith('https://bwc.gdut.edu.cn/')
    assert captured['url'] == qa.ENDPOINT
    assert captured['json']['model'] == 'XingChenAGI/Xing4.0-29B'
    assert captured['json']['enable_thinking'] is False
    assert captured['url'] == 'https://api.siliconflow.cn/v1/chat/completions'
    assert 'test-secret-not-real' not in result.model_dump_json()


@pytest.mark.parametrize('status,expected', [(401,503),(403,503),(429,429),(500,502)])
def test_provider_errors_are_sanitized(monkeypatch, status, expected):
    install_response(monkeypatch, status=status)
    with pytest.raises(HTTPException) as result:
        qa.generate('地址', [{'id':'x','title':'t','content':'c','source_type':'official'}])
    assert result.value.status_code == expected
    assert 'test-secret' not in result.value.detail


@pytest.mark.parametrize('content', [[], {'status':'answered','answer':'unknown','source_ids':['fake']},
    {'status':'answered','answer':'unknown','source_ids':[]}, {'status':'answered','answer':5,'source_ids':[]}])
def test_malformed_answer_and_fake_citations_rejected(monkeypatch, content):
    install_response(monkeypatch, content=content)
    with pytest.raises(HTTPException) as result:
        qa.generate('地址', [{'id':'x','title':'t','content':'c','source_type':'official'}])
    assert result.value.status_code == 502


def test_missing_key_and_unapproved_model(monkeypatch):
    for settings in [('',qa.MODEL), ('test','paid-model')]:
        monkeypatch.setattr(qa,'settings',lambda: settings)
        with pytest.raises(HTTPException) as result:
            qa.generate('地址', [])
        assert result.value.status_code == 503


def test_provider_settings_never_reuse_zhipu_key(monkeypatch, tmp_path):
    (tmp_path/'.env').write_text('ZHIPU_API_KEY=old-test-only\nSILICONFLOW_API_KEY=new-test-only\n',encoding='utf-8')
    monkeypatch.setattr(qa,'ROOT',tmp_path)
    monkeypatch.delenv('SILICONFLOW_API_KEY',raising=False)
    monkeypatch.delenv('SILICONFLOW_MODEL',raising=False)
    monkeypatch.setenv('ZHIPU_API_KEY','old-environment-test-only')
    assert qa.settings() == ('new-test-only','XingChenAGI/Xing4.0-29B')


def test_busy_provider_message(monkeypatch):
    install_response(monkeypatch, status=503)
    with pytest.raises(HTTPException) as result:
        qa.generate('地址', [])
    assert result.value.status_code == 503 and '硅基流动' in result.value.detail


def test_overload_recovers_with_bounded_backoff(monkeypatch):
    waits = []
    monkeypatch.setattr(qa, 'sleep', waits.append)
    monkeypatch.setattr(qa, 'uniform', lambda *_: 0)
    class Client:
        calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            return httpx.Response(503,json={}) if self.calls<3 else httpx.Response(200,json={})
    client = Client()
    assert qa.request_model(client, 'test', {}).status_code == 200
    assert client.calls == 3 and waits == [2,4]


def test_no_retry_for_account_rate_limit(monkeypatch):
    monkeypatch.setattr(qa, 'sleep', lambda _: pytest.fail('Do not retry account limits'))
    class Client:
        calls = 0
        def post(self,*args,**kwargs):
            self.calls+=1
            return httpx.Response(429,json={'error':{'code':'1302'}})
    client = Client()
    assert qa.request_model(client,'test',{}).status_code == 429 and client.calls==1


def test_overload_stops_after_three_requests(monkeypatch):
    monkeypatch.setattr(qa,'sleep',lambda _:None)
    class Client:
        calls=0
        def post(self,*args,**kwargs):
            self.calls+=1
            return httpx.Response(503,json={})
    client=Client()
    assert qa.request_model(client,'test',{}).status_code==503 and client.calls==3


def test_question_endpoint_validation_and_limit(client, monkeypatch):
    qa._calls.clear()
    monkeypatch.setattr(qa,'answer_question',lambda _: qa.Answer(answer='资料不足', status='insufficient_evidence', sources=[], model=None))
    assert client.post('/api/assistant/ask',json={'question':' '}).status_code == 422
    assert client.post('/api/assistant/ask',json={'question':'a'*601}).status_code == 422
    for _ in range(10):
        assert client.post('/api/assistant/ask',json={'question':'测试问题'}).status_code == 200
    assert client.post('/api/assistant/ask',json={'question':'测试问题'}).status_code == 429
    qa._calls.clear()
