# GitHub 与 HTTPS

## 当前阶段

已建立本机 main 分支、整理忽略规则与 GitHub Actions 检查流程。数据库密码、API Key、管理员凭据、数据库备份、原始研究下载与个人源码备份不提交。GitHub 远程仓库需要有效登录及可访问的 GitHub 网络连接；本机提交不能等同于已上传。

仓库建议名为 gdut-campus-navigator，首次建立为私有仓库。确认底图与学校标识的公开再传播许可后再考虑公开源码。创建空仓库时不要另加 README，以便保留本机完整提交；然后按 GitHub 页面提供的地址设置 origin 并 push main。不要向聊天发送密码或个人访问令牌。

GitHub Actions 包含 Python 3.13 后端测试与 Node 22 前端构建；只有实际推送并观察 GitHub 工作流结果后才能宣称云端 CI 通过。

## 没有服务器与域名时

使用 Cloudflare Quick Tunnel 可为本机 8080 服务分配临时 HTTPS 地址，不要求购买服务器或域名：

```powershell
.\scripts\start-public-preview.ps1
```

当前地址保存在 `.runtime/public-url.txt`，不提交版本库。停止入口：

```powershell
.\scripts\stop-public-preview.ps1
```

需先完成 Docker 构建并启动应用；脚本更新允许来源和 Secure Cookie 配置，不修改数据库密码和模型密钥。此脚本复用现有入口，进程重启后网址可能改变，需要重新运行脚本同步来源。若外网受阻，地址分配及连接登记本身不能作为网站可访问证明。

电脑与 Docker 必须保持运行；Quick Tunnel 不保证可用性，不能作为永久简历地址。不要把数据库端口或本机其他服务转发出去。

## 正式域名 HTTPS

准备可运行 Docker 的服务器及解析到它的域名，开放 80/443，设置 `.env.deploy` 的 PUBLIC_DOMAIN（仅域名，不含 https://），然后：

```bash
docker compose --env-file .env.deploy -f docker-compose.yml -f docker-compose.https.yml up -d --build
```

合并配置移除前后端的直接主机端口，只由 Caddy 暴露 80/443。Caddy 为域名申请并续期证书；管理员允许来源固定为对应 HTTPS 域名，登录 Cookie 标记为 Secure。caddy-data 必须持久化，避免丢失证书状态。

公网完成标准：HTTPS 根页面、健康接口、校园地图、模型问答、管理员登录和退出均通过；再测试重启与数据备份恢复。目前没有服务器和域名，正式部署尚未开始。

依据：Cloudflare Quick Tunnel 文档 https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ ，Caddy 自动 HTTPS 文档 https://caddyserver.com/docs/automatic-https 。

## 2026-11-24 本次实测

校徽已在首页、管理入口和浏览器图标中更新，前端构建通过。本机 main 分支与首次提交已完成；已扫描拟提交文本，未发现本机实际密钥值。GitHub MCP、网页及 Git Credential Manager 设备登录均遇到连接中断，未建立远程仓库、未推送，CI 未在 GitHub 运行。

已分配过临时 HTTPS 域名并登记过 Cloudflare 边缘连接；原生 curl 一度通过 TLS 收到应用的 405（对只允许 GET 的健康接口发送了 HEAD）。随后 GET 检查出现 Cloudflare 1033，连接日志显示 7844 端口超时，稳定外网验收未通过。测试入口已停止，不作为可用上线地址交付。本机服务仍运行。后续网络恢复后可运行启动脚本重新分配并验收入口，不能关闭证书校验来替代网络修复。
