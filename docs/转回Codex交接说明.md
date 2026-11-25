# 转回 Codex 交接说明（2026-11-23）

## 一、当前状态

项目接续开发已完成阶段 6、7、8，全部保持原目录结构、文档命名与代码风格。

| 阶段 | 内容 | 状态 | 验收文件 |
|---|---|---|---|
| 6 | AI 知识问答（RAG） | ✅ 真实模型调用通过 | `docs/stage-6-check.json`（passed） |
| 7 | AI 工具调用规划路线 | ✅ 真实工具调用通过 | `docs/stage-7-check.json` |
| 8 | Docker 三容器部署 | ✅ 本机实测通过 | `docs/stage-8-check.json`（passed） |

全项目 **84 项测试通过**，前端构建通过，容器环境内也复测通过。

## 二、本轮改了什么

**阶段 6（收尾验收）**
- 换用硅基流动 `XingChenAGI/Xing4.0-29B`，旧智谱配置不再读取；`.env` 填 `SILICONFLOW_API_KEY` / `SILICONFLOW_MODEL`。
- 真实问答返回官方来源，无资料问题正确拒答。修订 `scripts/check_assistant.py` 中写死的测试数（62 → 84）。

**阶段 7（新功能）**
- 后端新增 `backend/app/place_resolver.py`（地点/别名解析）、`backend/app/tool_assistant.py`（`/api/assistant/route`、function calling、限速、错误脱敏），注册进 `main.py`。
- 设计约束：模型只抽取地点短语，后端用真实地点表解析 ID 并调用 Dijkstra 算路；模型不接触任何距离/编号，无法编造路线。
- 前端 `AssistantPanel.vue` 改为双模式，`App.vue` 接收路线事件同步地图高亮，`assistant.css` 追加样式。
- 新增 `backend/tests/test_tool_assistant.py`（18 项）、`scripts/check_route_assistant.py`、`docs/阶段7讲解.md`。

**阶段 8（部署）**
- 新增 `docker-compose.yml`、`.dockerignore`、`.env.deploy.example`、`backend/Dockerfile`、`scripts/docker-entrypoint.sh`、`frontend/Dockerfile`、`frontend/nginx.conf`、`docs/阶段8讲解.md`。
- entrypoint 自动完成"等数据库 → 建库 → 迁移 → 导入示例数据 → 创建管理员 → 启动服务"，幂等。
- 国内环境适配：基础镜像走 daocloud/1ms.run 拉取后打官方 tag；Dockerfile 内置清华 pip + 淘宝 npm 源；`scripts/docker_fix_windows.ps1` 处理 Docker Desktop 4.99 的 socket 残留问题（管理员运行一次即可）。

## 三、怎么跑

**本地开发**：`.env` 配好密钥后，后端 `uvicorn backend.app.main:app --reload --port 8000`，前端 `npm run dev`（5173）。

**容器部署**：复制 `.env.deploy.example` 为 `.env.deploy` 并填密码/Key，然后
```
docker compose --env-file .env.deploy up -d --build
```
访问 `http://127.0.0.1:8080/`。当前容器已在运行。

## 四、已知边界（接手时务必注意）

1. **数据是课程示例，不是真实校园数据**。12 个地点、18 条道路、Leaflet 人工平面示意坐标均来自示例；7 条知识资料只是起步资料。项目红线：**不可用于真实导航**。真实采集规则见 `data/real/collection-plan.json`，尚未执行。
2. **阶段 8 只做到本机容器化**。README 里"公开网址可访问"这一目标还需部署云服务器 + 域名 + HTTPS，未做。
3. 本目录**不是 git 仓库**（`git status` 会报 not a git repository）。转回 Codex 时直接复制整个目录；若要版本管理需自行 `git init`。
4. `.env` / `.env.deploy` 含密钥，已被 `.gitignore` 排除，不要提交或外发。
