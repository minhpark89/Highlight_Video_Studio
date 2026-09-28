[CmdletBinding()]
param(
    [string]$SshAlias = "vps",
    [int]$RemotePort = 15080,
    [int]$LocalPort = 5080,
    [int]$RetrySeconds = 15
)

$ErrorActionPreference = "Stop"
$stateDir = Join-Path $PSScriptRoot "state"
$logFile = Join-Path $stateDir "highlight_reverse_tunnel.log"
$lockFile = Join-Path $stateDir "highlight_reverse_tunnel.lock"
New-Item -ItemType Directory -Path $stateDir -Force | Out-Null

function Write-TunnelLog([string]$Message) {
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding UTF8
    Write-Output $line
}

if (Test-Path $lockFile) {
    $existingPid = Get-Content $lockFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($existingPid -match "^\d+$") {
        $existing = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
        if ($existing) {
            Write-TunnelLog "Supervisor already active as PID $existingPid; exiting."
            exit 0
        }
    }
}
Set-Content -Path $lockFile -Value $PID -Encoding ASCII -Force

try {
    while ($true) {
        $localReady = Test-NetConnection -ComputerName 127.0.0.1 -Port $LocalPort -InformationLevel Quiet -WarningAction SilentlyContinue
        if (-not $localReady) {
            Write-TunnelLog "Local app 127.0.0.1:$LocalPort is unavailable; retrying in $RetrySeconds seconds."
            Start-Sleep -Seconds $RetrySeconds
            continue
        }

        $sshArgs = @(
            "-N", "-T",
            "-o", "BatchMode=yes",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-R", "127.0.0.1:${RemotePort}:127.0.0.1:${LocalPort}",
            $SshAlias
        )
        Write-TunnelLog "Opening loopback-only reverse tunnel vps 127.0.0.1:$RemotePort -> PC 127.0.0.1:$LocalPort."
        & ssh.exe @sshArgs
        $exitCode = $LASTEXITCODE
        Write-TunnelLog "SSH exited with code $exitCode; retrying in $RetrySeconds seconds."
        Start-Sleep -Seconds $RetrySeconds
    }
}
finally {
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
