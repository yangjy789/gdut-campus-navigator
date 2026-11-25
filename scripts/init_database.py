"""创建项目专用数据库，不修改已有数据库。"""
import re

from sqlalchemy import create_engine, text

from backend.app.config import database_url


def main():
    url = database_url()
    name = url.database
    if not name or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}', name):
        raise ValueError('DB_NAME 只允许以字母开头的字母、数字与下划线')
    # URL.set(database=None) 会保留旧值；_replace 才会清除数据库名称。
    engine = create_engine(url._replace(database=None), connect_args={'connect_timeout': 5})
    try:
        with engine.begin() as connection:
            connection.execute(text(f'CREATE DATABASE IF NOT EXISTS `{name}` CHARACTER SET utf8mb4'))
        print('Project database is ready. Next: python -m alembic upgrade head')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
