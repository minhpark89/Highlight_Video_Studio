# Safe Watchdog for Highlight Video Studio (Port 5080)
# Requirements:
# 1. Check Process + Port (3 retries, 5s apart before declaring down)
# 2. Cleanup before start: Kill any hanging process occupying port 5080 or zombie app.py
# 3. Anti-spam loop: If restart fails 3 consecutive times, enter backoff (180s)
# 4. Singleton lock to prevent duplicate watchdog instances

$ErrorActionPreference = "Continue"
$workDir = "D:\Highlight_Video_Studio"
$pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python313\pythonw.exe"
$port = 5080
$logFile = Join-Path $workDir "watchdog.log"
$lockFile = Join-Path $workDir "watchdog.lock"

function Log-Message([string]$msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $entry = "[$ts] $msg"
    Write-Output $entry
    try {
        Add-Content -Path $logFile -Value $entry -ErrorAction SilentlyContinue
    } catch {}
}

# 0. Singleton watchdog check via lockfile + PID validation
try {
    if (Test-Path $lockFile) {
        $existingPid = Get-Content $lockFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existingPid -match "^\d+$") {
            $p = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
            if ($p -and $p.Id -ne $PID) {
                # Verify it is actually powershell
                if ($p.ProcessName -like "*powershell*") {
                    Log-Message "Another watchdog instance already active (PID: $existingPid). Exiting."
                    exit 0
                }
            }
        }
    }
    Set-Content -Path $lockFile -Value $PID -Encoding ASCII -Force
} catch {
    Log-Message "Warning: Failed to setup lock file: $_"
}

Log-Message "Watchdog 5080 started (PID: $PID)"

function Test-PortResponding([int]$targetPort) {
    $ok = $false
    try {
        $tcp = New-Object Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", $targetPort, $null, $null)
        $waitOk = $iar.AsyncWaitHandle.WaitOne(2000, $false)
        if ($waitOk) {
            $tcp.EndConnect($iar)
            $ok = $true
        }
        $tcp.Close()
    } catch {
        $ok = $false
    }
    return $ok
}

function Cleanup-PortAndHangingProcesses([int]$targetPort) {
    Log-Message "Cleaning up port $targetPort and lingering processes..."
    
    # Kill process occupying port
    try {
        $conns = Get-NetTCPConnection -LocalPort $targetPort -State Listen -ErrorAction SilentlyContinue
        foreach ($conn in $conns) {
            $pidToKill = $conn.OwningProcess
            if ($pidToKill -and $pidToKill -gt 4) {
                Log-Message "Terminating process occupying port $targetPort (PID: $pidToKill)..."
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {}

    # Kill any zombie python/pythonw running web\app.py under D:\Highlight_Video_Studio
    try {
        $zombies = Get-CimInstance Win32_Process | Where-Object {
            ($_.Name -eq "python.exe" -or $_.Name -eq "pythonw.exe") -and
            $_.CommandLine -like "*Highlight_Video_Studio*web\app.py*"
        }
        foreach ($z in $zombies) {
            Log-Message "Terminating lingering Highlight Studio process (PID: $($z.ProcessId))..."
            Stop-Process -Id $z.ProcessId -Force -ErrorAction SilentlyContinue
        }
    } catch {}

    Start-Sleep -Seconds 2
}

function Start-HighlightStudio() {
    Log-Message "Starting Highlight Video Studio backend..."
    try {
        Start-Process -FilePath $pythonPath -ArgumentList "web\app.py" -WorkingDirectory $workDir -WindowStyle Hidden
        Log-Message "Backend launch invoked."
    } catch {
        Log-Message "ERROR: Failed to launch backend: $_"
    }
}

$consecutiveFailures = 0

while ($true) {
    $isHealthy = $false

    # Step 1: Health check with 3 retries (5s apart)
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        if (Test-PortResponding -targetPort $port) {
            $isHealthy = $true
            break
        }
        if ($attempt -lt 3) {
            Start-Sleep -Seconds 5
        }
    }

    if ($isHealthy) {
        if ($consecutiveFailures -gt 0) {
            Log-Message "Port $port recovered successfully. Resetting failure counter."
            $consecutiveFailures = 0
        }
        # Normal check interval when healthy
        Start-Sleep -Seconds 15
        continue
    }

    # If unhealthy after 3 retries:
    $consecutiveFailures++
    Log-Message "Port $port down (Strike $consecutiveFailures/3)."

    # Step 2: Cleanup and restart
    Cleanup-PortAndHangingProcesses -targetPort $port
    Start-HighlightStudio

    # Wait for service startup
    Start-Sleep -Seconds 6

    # Verify if it recovered
    if (Test-PortResponding -targetPort $port) {
        Log-Message "Service restarted and port $port responding OK."
        $consecutiveFailures = 0
        Start-Sleep -Seconds 15
        continue
    }

    # Step 3: Anti-spam loop backoff
    if ($consecutiveFailures -ge 3) {
        $backoffSeconds = 180
        Log-Message "WARNING: Restart failed 3 consecutive times! Entering backoff mode for $backoffSeconds seconds (3 minutes)..."
        Start-Sleep -Seconds $backoffSeconds
        # After backoff, allow fresh retry streak
        $consecutiveFailures = 2
    } else {
        Start-Sleep -Seconds 10
    }
}
