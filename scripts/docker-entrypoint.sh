#!/bin/sh
# 容器启动时初始化数据库与管理员，再交给 CMD 启动服务。幂等，可重复执行。
set -e

# create_admin 会把随机密码写入 .runtime；确保目录存在且属主正确。
mkdir -p /app/.runtime/chroma

echo "[entrypoint] 等待数据库 ${DB_HOST}:${DB_PORT} 就绪..."
python - <<'PY'
import os, time
from sqlalchemy import create_engine, text
from backend.app.config import database_url

url = database_url()
# 初次启动数据库可能未建库，先用不含数据库名的 URL 等待服务器可用。
probe = url._replace(database=None)
for _ in range(60):
    try:
        engine = create_engine(probe, connect_args={'connect_timeout': 3})
        with engine.connect() as c:
            c.execute(text('SELECT 1'))
        engine.dispose()
        print('[entrypoint] 数据库服务器已就绪')
        break
    except Exception:
        time.sleep(2)
else:
    raise SystemExit('数据库在 120 秒内未就绪')
PY

echo "[entrypoint] 创建数据库（若不存在）..."
python -m scripts.init_database
echo "[entrypoint] 执行迁移..."
python -m alembic upgrade head
echo "[entrypoint] 仅对未初始化空库导入课程示例，保留已有编辑与删除..."
python -m scripts.seed_demo
echo "[entrypoint] 初始化管理员（幂等）..."
python -m scripts.create_admin

echo "[entrypoint] 启动服务: $*"
exec "$@"
