[CmdletBinding(DefaultParameterSetName = "Preview")]
param(
    [Parameter(ParameterSetName = "Register", Mandatory = $true)]
    [switch]$Register,
    [Parameter(ParameterSetName = "Unregister", Mandatory = $true)]
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$taskName = "HighlightVideoStudio_ReverseTunnel"
$appTaskName = "HighlightVideoStudio_5080"
$supervisor = Join-Path $PSScriptRoot "highlight_reverse_tunnel.ps1"

if (-not (Test-Path $supervisor)) {
    throw "Tunnel supervisor not found: $supervisor"
}

if ($Register) {
    if (-not (Get-ScheduledTask -TaskName $appTaskName -ErrorAction SilentlyContinue)) {
        throw "Existing app task $appTaskName was not found; refusing to register the tunnel task."
    }
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        throw "Task $taskName already exists. Unregister it explicitly before replacing it."
    }

    $arguments = '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $supervisor
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Loopback-only reverse SSH tunnel for Highlight Video Studio" | Out-Null
    Write-Output "Registered $taskName. Start it only after VPS task task_4e2b9ac158b6 confirms the loopback endpoint is ready."
    exit 0
}

if ($Unregister) {
    if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output "Removed $taskName. The app task $appTaskName was not changed."
    } else {
        Write-Output "$taskName is not registered. Nothing changed."
    }
    exit 0
}

Write-Output "Preview only: no scheduled task was created."
Write-Output "Later registration: powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Register"
Write-Output "Then activate: Start-ScheduledTask -TaskName $taskName"
Write-Output "Rollback: powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Unregister"
