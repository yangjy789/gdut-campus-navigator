$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath (Join-Path $taskRoot 'frontend')
try {
    npm run dev
} finally {
    Pop-Location
}
