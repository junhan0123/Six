# start.ps1 - Xiao6 launcher core (Phase 31.1 + R8 Release Closure)
# Only: resolve paths -> check backend -> start backend if needed -> wait health -> start Electron (skip if missing) -> logs/PID
# No system setting changes / no registry / no autostart / no dependency install.
# NOTE: this script is intentionally ASCII-only so PowerShell 5.1 (ANSI default) parses it correctly.
$ErrorActionPreference = 'Continue'
$LauncherDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ConfigPath  = Join-Path $LauncherDir 'launcher_config.json'
$ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

# -- R8 Release Closure: built-in default config. Missing launcher_config.json no longer exits;
#    backend starts with defaults (Electron optional) so a fresh git clone runs out of the box. --
$DefaultCfg = [ordered]@{
    version   = '1.0.0-rc1'
    project   = [ordered]@{ root = '..' }
    logs      = [ordered]@{ dir = 'logs'; startup_log = 'logs/startup.log' }
    pid_files = [ordered]@{ backend = 'backend.pid'; electron = 'electron.pid' }
    backend   = [ordered]@{
        host = '127.0.0.1'; port = 8000; script = 'server.py'; python_bin = ''
        health_endpoint = '/api/health'; health_timeout_sec = 60
        log_file = 'logs/backend.out.log'
    }
    electron  = [ordered]@{
        bin = 'electron-bin/electron.exe'; args = ''; url = 'http://127.0.0.1:8000'
        log_file = 'logs/electron.out.log'
    }
}

$cfg = $null
if (Test-Path $ConfigPath) {
    try {
        $cfg = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    } catch {
        Write-Warning "Config parse failed ($ConfigPath), falling back to built-in defaults: $_"
    }
}
if ($null -eq $cfg) {
    Write-Warning "Missing $ConfigPath - using built-in default config (will NOT exit)"
    $cfg = [PSCustomObject]$DefaultCfg
}

$ProjRoot  = Resolve-Path (Join-Path $LauncherDir $cfg.project.root)
$LogsDir   = Join-Path $LauncherDir $cfg.logs.dir
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null
$StartLog  = Join-Path $LauncherDir $cfg.logs.startup_log
$BackendPIDFile  = Join-Path $LauncherDir $cfg.pid_files.backend
$ElectronPIDFile = Join-Path $LauncherDir $cfg.pid_files.electron
$ErrDir = $LogsDir

function Log($msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Write-Output $line
    Add-Content -Path $StartLog -Value $line -Encoding UTF8
}

"$ts [START] Xiao6 launcher v$($cfg.version)" | Set-Content -Path $StartLog -Encoding UTF8
Log "Project root: $ProjRoot"

# Port: environment variable overrides config
$Port = $cfg.backend.port
if ($env:XIAO6_PORT) { $Port = $env:XIAO6_PORT }
$HealthURL = "http://$($cfg.backend.host):$Port$($cfg.backend.health_endpoint)"
$BackendLog  = Join-Path $LauncherDir $cfg.backend.log_file
$ElectronLog = Join-Path $LauncherDir $cfg.electron.log_file

function Test-Backend {
    try {
        $r = Invoke-WebRequest -Uri $HealthURL -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

# -- 0.5 Clear possibly-injected wrong AGNES keys so .env stays the single source of truth --
Remove-Item Env:\AGNES_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:\AGNES_BASE_URL -ErrorAction SilentlyContinue
Remove-Item Env:\AGNES_MODEL -ErrorAction SilentlyContinue
Log "Cleared env AGNES_API_KEY/AGNES_BASE_URL/AGNES_MODEL; .env will be used"

# -- 1. Check backend --
$backendRunning = Test-Backend
if ($backendRunning) {
    Log "Backend already running (HTTP 200 @ $HealthURL), skip start"
} else {
    # -- 2. Resolve python --
    # 依次探测 python3 / python，取第一个【实际可执行】的解释器。
    # 原因：Windows 上 python3 常解析到 Microsoft Store 的 App Execution Alias 存根，
    # 它"能被 Get-Command 找到"却"无法非交互执行"（报：系统无法访问此文件），
    # 直接拿它启动后端会失败。故必须实测执行，而非仅判断是否存在。
    $py = $cfg.backend.python_bin
    if (-not $py) {
        $pyCandidates = @()
        foreach ($name in @('python3', 'python')) {
            $cmd = Get-Command $name -ErrorAction SilentlyContinue
            if ($cmd -and ($pyCandidates -notcontains $cmd.Source)) { $pyCandidates += $cmd.Source }
        }
        foreach ($cand in $pyCandidates) {
            try {
                & $cand -c "import sys" 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $py = $cand; break }
            } catch { }
        }
        if (-not $py -and $pyCandidates.Count -gt 0) { $py = $pyCandidates[0] }
    }
    if (-not $py) {
        Log "ERROR: python not found (python3/python); install Python or set backend.python_bin in launcher_config.json"
        exit 1
    }
    Log "Python interpreter: $py"
    # -- 3. Start backend --
    try {
        $p = Start-Process -FilePath $py -ArgumentList $cfg.backend.script `
            -WorkingDirectory $ProjRoot `
            -RedirectStandardOutput $BackendLog -RedirectStandardError (Join-Path $ErrDir 'backend.err') `
            -PassThru
        $p.Id | Set-Content -Path $BackendPIDFile -Encoding ascii
        Log "Backend started PID=$($p.Id)"
    } catch {
        Log "ERROR: backend start failed: $_"
        exit 1
    }
    # -- 4. Wait for health --
    $deadline = (Get-Date).AddSeconds($cfg.backend.health_timeout_sec)
    $ok = $false
    while ((Get-Date) -lt $deadline) {
        if (Test-Backend) { $ok = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ok) {
        Log "ERROR: backend health timeout ($HealthURL); see $BackendLog"
        exit 1
    }
    Log "Backend health OK ($HealthURL)"
}

# -- 5. Start Electron avatar window (R8 Release Closure: skip gracefully when runtime OR app entry missing) --
Remove-Item Env:\ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
Remove-Item Env:\NODE_OPTIONS -ErrorAction SilentlyContinue
$EbinPath = Join-Path $LauncherDir $cfg.electron.bin
$EappPath = $null
if ($cfg.electron.args) { $EappPath = Join-Path $ProjRoot $cfg.electron.args }
if ((Test-Path $EbinPath) -and $EappPath -and (Test-Path $EappPath)) {
    try {
        $ebin = (Resolve-Path $EbinPath).Path
        $p = Start-Process -FilePath $ebin -ArgumentList @($EappPath) `
            -WorkingDirectory $ProjRoot `
            -RedirectStandardOutput $ElectronLog -RedirectStandardError (Join-Path $ErrDir 'electron.err') `
            -PassThru
        $p.Id | Set-Content -Path $ElectronPIDFile -Encoding ascii
        Log "Electron started PID=$($p.Id) -> $($cfg.electron.url)"
    } catch {
        Log "ERROR: Electron start failed: $_"
        exit 1
    }
} else {
    Log "WARN: Electron skipped (runtime binary or app entry missing: $EbinPath / $EappPath) - backend-only mode, API still served"
}

Log "[DONE] Backend: $(if($backendRunning){'already-running'}else{'started'}), Electron: $(if(Test-Path $ElectronPIDFile){(Get-Content $ElectronPIDFile -Raw).Trim()}else{'skipped(optional)'})"
