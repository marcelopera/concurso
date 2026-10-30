param([switch]$Stop)

$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonExe = (Get-Command python -ErrorAction Stop).Source
$port = 8765
$appUrl = "http://127.0.0.1:$port"
$healthUrl = "$appUrl/api/health"
$dataDirectory = if ($env:ESTUDO_DB) { Split-Path -Parent $env:ESTUDO_DB } elseif ($env:ESTUDO_DATA_DIR) { $env:ESTUDO_DATA_DIR } else { Join-Path $appRoot 'data/estudo' }
$pidFile = Join-Path $dataDirectory 'servidor.pid'
$planFile = if ($env:ESTUDO_PLAN_FILE) { $env:ESTUDO_PLAN_FILE } else { Join-Path $appRoot 'plans/apofp-2026/roadmap.json' }

if ($Stop) {
    if (-not (Test-Path -LiteralPath $pidFile)) {
        Write-Output 'Não há processo iniciado por este launcher.'
        exit 0
    }
    $serverPid = 0
    if (-not [int]::TryParse((Get-Content -LiteralPath $pidFile -Raw).Trim(), [ref]$serverPid)) {
        Remove-Item -LiteralPath $pidFile -Force
        throw 'O arquivo do processo não contém um PID válido.'
    }
    $processInfo = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $serverPid"
    if ($processInfo -and $processInfo.CommandLine -and $processInfo.CommandLine -match '-m\s+estudo\s+serve' -and $processInfo.CommandLine.IndexOf($planFile, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
        Stop-Process -Id $serverPid -ErrorAction Stop
        Remove-Item -LiteralPath $pidFile -Force
        Write-Output 'Servidor local encerrado.'
    } else {
        Remove-Item -LiteralPath $pidFile -Force
        Write-Output 'O servidor já estava encerrado.'
    }
    exit 0
}

function Test-StudyServer {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 1 -Method Get
        return [bool]$health.ok
    } catch {
        return $false
    }
}

if (Test-StudyServer) {
    Start-Process $appUrl
    Write-Output "Aplicativo aberto em $appUrl"
    exit 0
}
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python não encontrado: $pythonExe"
}
New-Item -ItemType Directory -Force -Path $dataDirectory | Out-Null
$planArgument = '"' + $planFile + '"'
$serverProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'estudo', 'serve', '--init-plan', $planArgument, '--port', [string]$port) -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru
Set-Content -LiteralPath $pidFile -Value $serverProcess.Id -NoNewline

$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    if (Test-StudyServer) { $ready = $true; break }
    if ($serverProcess.HasExited) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    if (-not $serverProcess.HasExited) { Stop-Process -Id $serverProcess.Id -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    throw "O servidor não ficou pronto na porta $port. Rode python -m estudo no PowerShell para ver a mensagem de erro."
}

Start-Process $appUrl
Write-Output "Aplicativo aberto em $appUrl"
