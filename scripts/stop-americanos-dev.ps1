# Stop ONLY the recorded local API/Vite processes, after checking their identity.
# Leave Docker and its persistent demo volume intact.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$record = Get-Item -LiteralPath (Join-Path $root '.local-dev\processes.json')
$ids = Get-Content -LiteralPath $record.FullName -Raw | ConvertFrom-Json
foreach ($entry in @(@{ id = $ids.api_pid; pattern = 'uvicorn.+app\.main:app.+--port\s+8010' }, @{ id = $ids.frontend_pid; pattern = 'vite[/\\]bin[/\\]vite\.js.+--port\s+5175' })) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($entry.id)"
    if (!$process) { continue }
    if ($process.CreationDate -gt $record.LastWriteTime -or $process.CommandLine -notmatch $entry.pattern) {
        throw "La identidad del proceso $($entry.id) cambio. No se detuvo."
    }
    & taskkill.exe /PID $entry.id /T /F
    if ($LASTEXITCODE -ne 0) { throw "No se pudo detener el proceso local $($entry.id)." }
}
Write-Output 'API y Vite locales detenidos. Base Docker y datos conservados.'
