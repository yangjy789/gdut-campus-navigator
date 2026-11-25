"""首次创建本机管理员，随机口令只写入被 Git 忽略的本地文件。"""
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.auth import hash_password
from backend.app.config import ROOT
from backend.app.database import make_engine
from backend.app.models import AdminUser


def main():
    engine = make_engine()
    try:
        with Session(engine) as session:
            if session.scalar(select(AdminUser.id).where(AdminUser.username == 'admin')) is not None:
                print('Admin already exists; no password reset performed.')
                return
            path = ROOT / '.runtime/admin-credentials.txt'
            path.parent.mkdir(exist_ok=True)
            password = secrets.token_urlsafe(24)
            # x 模式：不覆盖已有的本机凭据文件。
            with path.open('x', encoding='utf-8') as stream:
                stream.write('Username: admin\nPassword: ' + password + '\n')
            session.add(AdminUser(username='admin', password_hash=hash_password(password), active=True))
            session.commit()
            print('Admin created. Credentials saved in .runtime/admin-credentials.txt (not printed).')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
