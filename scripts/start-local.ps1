$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $project
if (!(Test-Path -LiteralPath "$project\web\out\index.html")) {
    throw 'Build the frontend first: cd web; npm ci; npm run build'
}
$env:MG_APP_ORIGIN = 'http://127.0.0.1:8000'
Write-Host 'MarginGuard is available at http://127.0.0.1:8000'
& "$project\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
