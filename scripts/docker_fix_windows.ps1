# Stage 8: Windows Docker engine repair script (RUN AS ADMINISTRATOR)
# Fixes: stale sailor-ingest.sock "Access is denied" on Docker Desktop 4.99
# Usage (Admin PowerShell): powershell -ExecutionPolicy Bypass -File docker_fix_windows.ps1
# NOTE: This file is intentionally ASCII-only to avoid PowerShell 5.1 encoding parse errors.

$ErrorActionPreference = 'SilentlyContinue'
$dockerDir = Join-Path $env:LOCALAPPDATA 'Docker'
$runDir    = Join-Path $dockerDir 'run'
$exe       = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\Docker Desktop.exe'
$ddcli     = Join-Path $env:LOCALAPPDATA 'Programs\DockerDesktop\DockerCli.exe'

Write-Host '[1/6] Stop Docker Desktop...'
if (Test-Path $ddcli) { & $ddcli -Shutdown 2>&1 | Out-Null }
Get-Process | Where-Object { $_.Name -match 'docker' } | Stop-Process -Force
Start-Sleep -Seconds 3

Write-Host '[2/6] Shutdown WSL...'
& 'C:\Program Files\WSL\wsl.exe' --shutdown 2>&1 | Out-Null
Start-Sleep -Seconds 5

Write-Host '[3/6] Take ownership of stale sockets...'
if (Test-Path $runDir) {
    Get-ChildItem $runDir -Force | ForEach-Object {
        takeown /F $_.FullName 2>&1 | Out-Null
        icacls $_.FullName /grant "$($env:USERNAME):(F)" /T 2>&1 | Out-Null
    }
}

Write-Host '[4/6] Delete stale sockets (with retry)...'
if (Test-Path $runDir) {
    for ($pass = 1; $pass -le 3; $pass++) {
        Get-ChildItem $runDir -Force | ForEach-Object {
            try {
                [System.IO.File]::Delete($_.FullName)
                Write-Host "  deleted: $($_.Name)"
            } catch {
                try { Remove-Item -LiteralPath $_.FullName -Force -Recurse -ErrorAction Stop; Write-Host "  removed: $($_.Name)" }
                catch { Write-Host "  retry $pass - still locked: $($_.Name)" }
            }
        }
        Start-Sleep -Seconds 2
    }
}
$remaining = @(Get-ChildItem $runDir -Force -ErrorAction SilentlyContinue)
Write-Host "  remaining sockets: $($remaining.Count)"

Write-Host '[5/6] Ensure registry mirrors configured...'
$settings = Join-Path $env:APPDATA 'Docker\settings-store.json'
if (Test-Path $settings) {
    $json = Get-Content $settings -Raw | ConvertFrom-Json
    $json | Add-Member -NotePropertyName 'registry-mirrors' -NotePropertyValue @('https://docker.m.daocloud.io','https://docker.1ms.run','https://docker.xuanyuan.me') -Force
    ($json | ConvertTo-Json -Depth 20) | Set-Content $settings -Encoding UTF8
    Write-Host '  mirrors written'
}

Write-Host '[6/6] Start Docker Desktop...'
Start-Process $exe
Write-Host ''
Write-Host 'DONE. Wait until Docker Desktop tray icon is green (no error dialog),'
Write-Host 'then come back and tell me. Do NOT close Docker Desktop afterwards.'
