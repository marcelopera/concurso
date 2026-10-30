param([switch]$Stop)

$ErrorActionPreference = 'Stop'
$appRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = 'C:\Users\marce\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$port = 8765
$appUrl = "http://127.0.0.1:$port"
$healthUrl = "$appUrl/api/health"
$dataDirectory = Join-Path $appRoot 'dados'
$pidFile = Join-Path $dataDirectory 'servidor.pid'
$serverScript = Join-Path $appRoot 'server.py'

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
    if ($processInfo -and $processInfo.CommandLine -and $processInfo.CommandLine.IndexOf($serverScript, [StringComparison]::OrdinalIgnoreCase) -ge 0) {
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
        return [bool]$health.ok -and [int]$health.content_occurrences -gt 0
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
    throw "Python do runtime não encontrado: $pythonExe"
}
if (-not (Test-Path -LiteralPath $serverScript)) {
    throw "Servidor não encontrado: $serverScript"
}

New-Item -ItemType Directory -Force -Path $dataDirectory | Out-Null
$scriptArgument = '"' + $serverScript + '"'
$serverProcess = Start-Process -FilePath $pythonExe -ArgumentList @($scriptArgument, '--port', [string]$port) -WorkingDirectory $appRoot -WindowStyle Hidden -PassThru
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
    throw "O servidor não ficou pronto na porta $port. Rode server.py no PowerShell para ver a mensagem de erro."
}

Start-Process $appUrl
Write-Output "Aplicativo aberto em $appUrl"
