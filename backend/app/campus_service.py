"""统一校园目录的地点识别与步行地图衔接，不生成未经测量的距离。"""
from typing import Annotated
from urllib.parse import urlencode
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.public_campus import catalog
from backend.app import qa, tool_assistant as ta
from backend.app.knowledge import tokens, vector

router = APIRouter(prefix='/api/campus/real', tags=['校园导览服务'])
DB = Annotated[Session, Depends(get_session)]


class PlanBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    start_id: str = Field(min_length=1,max_length=64)
    end_id: str = Field(min_length=1,max_length=64)


def resolve(text, places):
    norm = lambda s: ''.join(s.casefold().split())
    text = norm(text)
    matches = [p for p in places if text and text in {norm(p['name']), *map(norm,p['aliases'])}]
    return matches[0] if len(matches)==1 else None


def prepare_navigation(start, end):
    if start['id']==end['id']:
        raise HTTPException(422,'起点与终点相同，请选择另一处地点')
    if start['planned'] or end['planned']:
        raise HTTPException(422,'规划中的地点暂不提供步行路线查询')
    prefix = '广东工业大学大学城校区'
    url = 'https://api.map.baidu.com/direction?' + urlencode({
        'origin':prefix+start['name'],'destination':prefix+end['name'],
        'mode':'walking','region':'广州市','output':'html','src':'webapp.gdut.campus'})
    return {'status':'navigation_ready','start':start,'end':end,
            'navigation_url':url,'provider':'百度地图','distance_m':None,
            'message':'起终点已确认，可在百度地图查看步行路线。请核对地图匹配的具体位置与通行情况。'}


@router.post('/route')
def route(body: PlanBody, session: DB):
    places = {p['id']:p for p in catalog(session)['places']}
    if body.start_id not in places or body.end_id not in places:
        raise HTTPException(404,'地点不存在或已更新，请刷新地点列表')
    return prepare_navigation(places[body.start_id],places[body.end_id])


@contextmanager
def assistant_slot(request):
    qa.check_rate_limit(request)
    if not qa._slots.acquire(blocking=False):
        raise HTTPException(429,'助手正在处理问题，请稍后重试')
    try:
        yield
    finally:
        qa._slots.release()


@router.post('/assistant/route')
def assistant_route(body: ta.RouteQuestion, request: Request, session: DB):
    with assistant_slot(request):
        places = catalog(session)['places']
        explicit = ta.explicit_route(body.question)
        if explicit:
            start, end = (resolve(t,places) for t in explicit)
            method = 'explicit_pattern'
        else:
            phrases = ta.extract_places(body.question, session)
            start, end = (resolve(t,places) for t in phrases)
            method = 'model_tool'
        if not start or not end:
            return {'status':'need_clarification','message':'请明确起点和终点。地点未收录或名称不唯一时，可在地点列表中选择。',
                    'extraction_method':method,'navigation_url':None}
        return {**prepare_navigation(start,end),'extraction_method':method}


def live_sources(question, session):
    # 官网目录从数据库读取，后台改名或删除后不能继续引用旧地点快照。
    base = [d for d in qa.get_index().retrieve(question) if not d['id'].startswith('public-place-')]
    qvec, terms = vector(question), tokens(question)
    ranked = []
    for p in catalog(session)['places']:
        content = f"{p['name']}位于{p['region']}，类别为{p['category']}。"
        if p['aliases']: content += '旧称或名称范围：'+'、'.join(p['aliases'])+'。'
        if p['planned']: content += '来源标为规划中，不确认已建成或开放。'
        content += p.get('description','') + '本记录不提供实时开放时间或道路距离。'
        text = p['name']+' '+' '.join(p['aliases'])+' '+content
        score = sum(a*b for a,b in zip(qvec,vector(text)))
        named = p['name'] in question or any(a and a in question for a in p['aliases'])
        if named or (terms & tokens(text) and score >= .12):
            ranked.append({'id':'public-place-'+p['id'],'title':p['name']+'地点资料',
                'content':content,'source_url':p['source_url'],
                'source_type':'official' if p.get('verification_status')=='official_document_only' else 'project',
                'verified_on':p['checked_on'],'score':1.0 if named else score})
    return sorted(base+ranked,key=lambda d:d.get('score',0),reverse=True)[:3]


@router.post('/ask',response_model=qa.Answer)
def ask(body: qa.Question, request: Request, session: DB):
    with assistant_slot(request):
        sources = live_sources(body.question,session)
        if not sources:
            return qa.Answer(answer='当前资料中未找到可靠依据，请尝试更具体的地点或问题。',
                             status='insufficient_evidence',sources=[],model=None)
        result = qa.generate(body.question,sources)
        return qa.Answer(answer=result['answer'],status=result['status'],model=qa.MODEL,
            sources=[qa.Source.model_validate(d) for d in sources if d['id'] in result['source_ids']])
