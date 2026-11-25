# 后端镜像：Python 3.13，仅安装运行依赖，不含 .env 与本机密钥。
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# 先复制依赖清单，利用 Docker 层缓存。
# 使用国内 PyPI 镜像，便于在国内网络环境构建（可通过 PIP_INDEX_URL 构建参数覆盖）。
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements-lock.txt /app/
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements-lock.txt

COPY backend /app/backend
COPY scripts /app/scripts
COPY data /app/data
COPY alembic.ini /app/
COPY backend/migrations /app/backend/migrations

# 非 root 运行。预先创建运行期目录并赋权：compose 挂载命名卷到 /app/.runtime 时，
# Docker 会继承镜像中该目录的属主，appuser 才能在卷内创建 chroma 子目录。
RUN useradd --create-home --shell /bin/bash appuser \
    && mkdir -p /app/.runtime/chroma \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
ENTRYPOINT ["sh", "/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
