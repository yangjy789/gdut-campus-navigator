"""从项目 .env 读取连接配置，密码不写进源码。"""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parents[2]


def database_url() -> URL:
    load_dotenv(ROOT / '.env', encoding='utf-8-sig')
    if not os.getenv('DB_USER') or not os.getenv('DB_PASSWORD'):
        raise RuntimeError('请先在项目 .env 中设置 DB_USER 和 DB_PASSWORD')
    return URL.create(
        'mysql+pymysql', username=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'], host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME', 'gdut_campus'), query={'charset': 'utf8mb4'},
    )
