function Assert-QuiescentRender([string]$Target, $Queue) {
    if (-not $Queue.is_paused) { throw 'Render intake must be paused' }
    $processes = @(Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $_.ExecutablePath.StartsWith($Target + '\', [StringComparison]::OrdinalIgnoreCase)
    })
    $children = @($processes | Where-Object { $_.Name -notin @('python.exe','Highlight_Desktop_Test.exe') })
    if ($children.Count) { throw 'A media subprocess is still active' }
    if (-not $Queue.active) { return @{active_waiters=0; subprocesses=0} }
    $python = @($processes | Where-Object { $_.Name -eq 'python.exe' })
    if ($python.Count -ne 1) { throw 'Expected exactly one installed Python server' }
    $sourceLines = Get-Content -LiteralPath (Join-Path $Target 'web\app.py') -Encoding UTF8
    $waitLine = 0
    $waitStart = 0
    for ($index = 0; $index -lt $sourceLines.Count; $index++) {
        if ($sourceLines[$index] -match 'while pressure\(BASE_DIR\)') {
            $waitStart = $index + 1
            for ($offset = 1; $offset -lt 6; $offset++) {
                if ($sourceLines[$index + $offset] -match 'time.sleep\(5\)') {
                    $waitLine = $index + $offset + 1
                }
            }
        }
    }
    if (-not $waitLine) { throw 'Cannot identify the installed capacity wait' }
    $dump = (& py-spy dump --pid $python[0].ProcessId 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect current render threads' }
    $threads = [regex]::Matches($dump, '(?ms)^Thread .*?(?=^Thread |\z)')
    $workers = @($threads | Where-Object { $_.Value.Contains('run_job_pipeline (app.py:') })
    if ($workers.Count -ne $Queue.active) { throw 'Render thread count changed during inspection' }
    foreach ($worker in $workers) {
        $inCapacityWait = $false
        for ($line = $waitStart; $line -le $waitLine; $line++) {
            if ($worker.Value.Contains("run_job_pipeline (app.py:$line)")) { $inCapacityWait = $true }
        }
        if (-not $inCapacityWait) {
            throw 'Render worker is doing work outside the capacity wait'
        }
    }
    return @{active_waiters=$workers.Count; subprocesses=0; python_pid=$python[0].ProcessId;
        all_waiting_for_capacity=$true; restart_requeues_existing_jobs=$true}
}
