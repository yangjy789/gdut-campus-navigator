"""本地管理员会话：密码 scrypt；数据库仅存会话摘要。"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.database import get_session
from backend.app.models import AdminSession, AdminUser

COOKIE = 'campus_admin'
COOKIE_PATH = '/api/admin'
SESSION_SECONDS = 8 * 60 * 60
router = APIRouter(prefix='/api/admin/auth', tags=['管理员登录'])
DB = Annotated[Session, Depends(get_session)]


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3, maxmem=67108864).hex()
    return f'scrypt${salt}${digest}'


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, salt, expected = stored.split('$')
        if algorithm != 'scrypt':
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3, maxmem=67108864).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


DUMMY_HASH = hash_password(secrets.token_urlsafe(24))


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token: str) -> str:
    return hashlib.sha256(('csrf:' + token).encode()).hexdigest()


def check_origin(request: Request):
    allowed = os.getenv('ADMIN_ALLOWED_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000').split(',')
    origin = request.headers.get('origin')
    if origin is not None and origin not in {s.strip() for s in allowed}:
        raise HTTPException(403, '请求来源不被允许')


def require_admin(request: Request, session: DB) -> AdminUser:
    token = request.cookies.get(COOKIE, '')
    record = session.get(AdminSession, token_hash(token)) if token else None
    user = session.get(AdminUser, record.user_id) if record else None
    if not record or record.expires_at <= now() or not user or not user.active:
        raise HTTPException(401, '请先登录管理员账号')
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        check_origin(request)
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), csrf_token(token)):
            raise HTTPException(403, '操作校验失败，请刷新页面后重试')
    return user


class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=256)


@router.post('/login')
def login(body: LoginBody, request: Request, response: Response, session: DB):
    check_origin(request)
    # 自定义请求头阻止普通跨站表单提交；未开放跨域凭据访问。
    if request.headers.get('x-admin-request') != '1':
        raise HTTPException(403, '请从管理员页面登录')
    ip = request.client.host if request.client else 'unknown'
    current = now()
    with request.app.state.login_lock:
        failures = request.app.state.login_failures
        for key in list(failures):
            failures[key] = [t for t in failures[key] if current - t < timedelta(minutes=5)]
            if not failures[key]:
                del failures[key]
        if len(failures.get(ip, [])) >= 10:
            raise HTTPException(429, '登录尝试过多，请五分钟后重试')
        # 预先计入，避免并发失败请求绕过限制。
        failures.setdefault(ip, []).append(current)
    user = session.scalar(select(AdminUser).where(AdminUser.username == body.username))
    valid = verify_password(body.password.get_secret_value(), user.password_hash if user else DUMMY_HASH)
    if not user or not user.active or not valid:
        raise HTTPException(401, '用户名或密码错误')
    with request.app.state.login_lock:
        request.app.state.login_failures.pop(ip, None)
    old = request.cookies.get(COOKIE)
    if old:
        session.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash(old)))
    session.execute(delete(AdminSession).where(AdminSession.expires_at <= current))
    token = secrets.token_urlsafe(32)
    session.add(AdminSession(token_hash=token_hash(token), user_id=user.id, expires_at=current + timedelta(seconds=SESSION_SECONDS)))
    session.commit()
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite='strict',
                        secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', path=COOKIE_PATH)
    response.headers['Cache-Control'] = 'no-store'
    return {'username': user.username, 'csrf_token': csrf_token(token)}


@router.get('/me')
def me(request: Request, response: Response, user: Annotated[AdminUser, Depends(require_admin)]):
    response.headers['Cache-Control'] = 'no-store'
    return {'username': user.username, 'csrf_token': csrf_token(request.cookies[COOKIE])}


@router.post('/logout', status_code=204)
def logout(request: Request, response: Response, session: DB, user: Annotated[AdminUser, Depends(require_admin)]):
    session.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash(request.cookies[COOKIE])))
    session.commit()
    response.delete_cookie(COOKIE, path=COOKIE_PATH, httponly=True, samesite='strict')
