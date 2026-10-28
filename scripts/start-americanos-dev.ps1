# Isolated Postgres in Docker; native API/Vite in development, NEVER a build.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$state = Join-Path $root '.local-dev'
$isolatedEnv = Join-Path $state 'no-inherited-settings.env'
if (Test-Path -LiteralPath $isolatedEnv) { throw "El archivo de aislamiento debe permanecer ausente: $isolatedEnv" }
if (!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath (Join-Path $frontend 'node_modules\vite\bin\vite.js'))) {
    throw 'Faltan dependencias locales: backend/.venv o frontend/node_modules.'
}
foreach ($port in @(8010, 5175)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "El puerto $port ya esta ocupado. No se detuvo ningun proceso existente."
    }
}
$config = @{
    LIGA_ENV_FILE = $isolatedEnv
    DATABASE_URL = 'postgresql+psycopg://liga_dev:liga-local-only@127.0.0.1:5544/liga_americanos_dev'
    SECRET_KEY = 'liga-americanos-local-only-change-me-2026'
    COOKIE_SECURE = 'false'
    COOKIE_SAMESITE = 'lax'
    CORS_ORIGINS = 'http://localhost:5175,http://127.0.0.1:5175'
    CLOUDINARY_CLOUD_NAME = ''
    CLOUDINARY_API_KEY = ''
    CLOUDINARY_API_SECRET = ''
    ADMIN_EMAIL = 'admin@liga.local'
    ADMIN_PASSWORD = 'Liga-local-2026!'
    VITE_API_URL = 'http://localhost:8010'
    PYTHONIOENCODING = 'utf-8'
}
$previous = @{}
try {
    foreach ($key in $config.Keys) {
        $previous[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
        [Environment]::SetEnvironmentVariable($key, $config[$key], 'Process')
    }
    & docker compose -f (Join-Path $root 'compose.dev.yml') up -d --no-build --wait
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar la base aislada.' }
    Push-Location $backend
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la migracion local.' }
        & $python -m app.seed
        if ($LASTEXITCODE -ne 0) { throw 'Fallo el seed local.' }
        & $python (Join-Path $PSScriptRoot 'seed-americano-demo.py')
        if ($LASTEXITCODE -ne 0) { throw 'Fallo la creacion del ejemplo local.' }
    } finally { Pop-Location }
    New-Item -ItemType Directory -Force -Path $state | Out-Null
    $api = Start-Process -FilePath $python -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8010', '--reload') -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'api.log') -RedirectStandardError (Join-Path $state 'api-error.log') -PassThru
    $vite = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5175', '--strictPort') -WorkingDirectory $frontend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $state 'frontend.log') -RedirectStandardError (Join-Path $state 'frontend-error.log') -PassThru
    @{ api_pid = $api.Id; frontend_pid = $vite.Id } | ConvertTo-Json | Set-Content (Join-Path $state 'processes.json')
    foreach ($url in @('http://localhost:8010/health', 'http://localhost:5175')) {
        $ready = $false
        for ($attempt = 0; $attempt -lt 40; $attempt++) {
            & curl.exe --noproxy '*' --silent --fail --max-time 2 $url > $null
            if ($LASTEXITCODE -eq 0) { $ready = $true; break }
            Start-Sleep -Milliseconds 500
        }
        if (!$ready) { throw "No respondio $url. Revisa los logs en .local-dev/." }
    }
    Write-Output 'Frontend: http://localhost:5175/admin/americanos'
    Write-Output 'API: http://localhost:8010/docs'
    Write-Output 'Usuario local: admin@liga.local / Liga-local-2026!'
    Write-Output 'Base aislada: liga_americanos_dev, Docker, puerto 5544. Produccion no se modifico.'
} finally {
    foreach ($key in $previous.Keys) { [Environment]::SetEnvironmentVariable($key, $previous[$key], 'Process') }
}
