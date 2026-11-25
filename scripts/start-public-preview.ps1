$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
if ($dockerCommand) { $dockerExe = $dockerCommand.Source }
else { $dockerExe = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe' }
if (-not (Test-Path -LiteralPath $dockerExe)) { throw '请先启动 Docker Desktop。' }
$runtimePath = Join-Path $taskRoot '.runtime'
New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
$tunnelName = 'gdut-public-tunnel'
$state = & $dockerExe inspect -f '{{.State.Running}}' $tunnelName 2>$null
if ($LASTEXITCODE -ne 0) {
    & $dockerExe run -d --name $tunnelName --restart unless-stopped cloudflare/cloudflared:latest tunnel --no-autoupdate --protocol http2 --url http://host.docker.internal:8080
    if ($LASTEXITCODE -ne 0) { throw '公网入口未启动，请检查网络与镜像下载。' }
} elseif ($state -ne 'true') {
    & $dockerExe start $tunnelName | Out-Null
}
$publicUrl = $null
$startedAt = (& $dockerExe inspect -f '{{.State.StartedAt}}' $tunnelName).Trim()
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    $logs = (& $dockerExe logs --since $startedAt $tunnelName 2>&1) -join "`n"
    $matchesFound = [regex]::Matches($logs, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($matchesFound.Count -gt 0) { $publicUrl = $matchesFound[$matchesFound.Count - 1].Value; break }
    Start-Sleep -Seconds 1
}
if (-not $publicUrl) { throw '尚未分配公网地址，请稍后重试。' }
[System.IO.File]::WriteAllText((Join-Path $runtimePath 'public-url.txt'), $publicUrl + "`n", [System.Text.UTF8Encoding]::new($false))
# 仅修改部署配置中的来源与 Cookie 标记，不触碰数据库密码或 API Key。
$pythonExe = Join-Path $taskRoot '.venv\Scripts\python.exe'
$updateCode = @'
import sys
from pathlib import Path
from dotenv import dotenv_values, set_key
root=Path(sys.argv[1]); url=sys.argv[2]; target=root/'.env.deploy'
values=dotenv_values(target)
origins=[s for s in values.get('ADMIN_ALLOWED_ORIGINS','').split(',') if s and 'trycloudflare.com' not in s]
origins=list(dict.fromkeys(origins+['http://localhost:5173','http://127.0.0.1:5173','http://localhost:8080','http://127.0.0.1:8080']))
set_key(target,'ADMIN_ALLOWED_ORIGINS',','.join(origins+[url]))
set_key(target,'COOKIE_SECURE','true')
'@
& $pythonExe -c $updateCode $taskRoot $publicUrl
if ($LASTEXITCODE -ne 0) { throw '无法更新 HTTPS 来源配置。' }
& $dockerExe compose --project-directory $taskRoot --env-file (Join-Path $taskRoot '.env.deploy') up -d --no-build backend frontend
if ($LASTEXITCODE -ne 0) { throw '项目服务未启动成功。' }
Write-Output "已分配临时地址：$publicUrl"
Write-Output '请在另一网络验证可访问性；地址分配不代表隧道连接和外网验收通过。关闭电脑或公网入口会中断访问。'
