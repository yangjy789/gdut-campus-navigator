$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$command = Get-Command docker -ErrorAction SilentlyContinue
$dockerExe = if ($command) { $command.Source } else { Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\resources\bin\docker.exe' }
& $dockerExe stop gdut-public-tunnel
if ($LASTEXITCODE -ne 0) { throw '未能停止公网入口，请在 Docker Desktop 中检查 gdut-public-tunnel。' }
Write-Output '公网入口已停止，本机项目和数据库继续运行。'
