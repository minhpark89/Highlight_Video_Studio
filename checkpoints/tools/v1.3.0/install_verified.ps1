param(
    [string]$RuntimeUrl = 'http://127.0.0.1:58601',
    [switch]$AllowReadOnlyReconciliationStop
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'upgrade_quiescence.ps1')
$taskRoot = 'E:\OPENCLAW\BOB'
$target = [IO.Path]::GetFullPath((Join-Path $taskRoot 'Highlight destop test'))
if ($target -ne 'E:\OPENCLAW\BOB\Highlight destop test') { throw 'Unexpected installation target' }
$source = Join-Path $taskRoot 'source-worktree'
$evidence = Join-Path $source 'checkpoints\evidence\v1.3.0'
$verified = Get-Content -LiteralPath (Join-Path $evidence 'installer_payload.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $verified.success) { throw 'Payload verification missing' }
if ((Get-FileHash -LiteralPath $verified.setup -Algorithm SHA256).Hash.ToLowerInvariant() -ne $verified.sha256) { throw 'Installer changed after verification' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.IO.Compression
$assembly = [Reflection.Assembly]::LoadFile($verified.setup)
$formType = $assembly.GetType('InstallerForm')
$flags = [Reflection.BindingFlags]'Static,NonPublic'
function InstallerMethod([string]$Name, [object[]]$Arguments) { $formType.GetMethod($Name, $flags).Invoke($null, $Arguments) }
$deadline = [DateTime]::UtcNow.AddMinutes(12)
$idle = $false
$readOnlyReconciliationStop = $false
do {
    $queue = Invoke-RestMethod -Uri "$RuntimeUrl/api/queue/status" -TimeoutSec 10
    $content = Invoke-RestMethod -Uri "$RuntimeUrl/api/content-studio/queue" -TimeoutSec 15
    $posts = Get-Content -LiteralPath (Join-Path $target 'posts.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    $publishing = @($posts | Where-Object { $_.status -eq 'publishing' })
    if (-not $queue.is_paused) { throw 'Render queue must be paused before upgrade' }
    $idle = -not ($content.running -or $publishing.Count)
    if ($idle) {
        try { $render = Assert-QuiescentRender $target $queue }
        catch { $idle = $false }
    }
    $scheduler = Invoke-RestMethod -Uri "$RuntimeUrl/api/scheduler/status" -TimeoutSec 10
    $idle = $idle -and -not $scheduler.cycle_active
    if (-not $idle -and $AllowReadOnlyReconciliationStop -and
        -not $content.running -and -not $publishing.Count -and $queue.active -eq 0) {
        $installedPython = @(Get-CimInstance Win32_Process | Where-Object {
            $_.ExecutablePath -and $_.ExecutablePath.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase) -and $_.Name -eq 'python.exe'
        } | Select-Object -First 1)
        if ($installedPython.Count -eq 1) {
            $dump = (& py-spy dump --pid $installedPython[0].ProcessId 2>&1) -join "`n"
            $hasReadOnlyMetaCheck = $dump.Contains('check_scheduled_reel') -or $dump.Contains('check_processing_reel')
            $hasWriteAction = $dump -match 'finish_existing_reel|publish_existing|publish_reel|post_first_comment|upload_video|stage_video'
            if ($hasReadOnlyMetaCheck -and -not $hasWriteAction) {
                $readOnlyReconciliationStop = $true
                $idle = $true
            }
        }
    }
    if (-not $idle) { Start-Sleep -Milliseconds 300 }
} while (-not $idle -and [DateTime]::UtcNow -lt $deadline)
if (-not $idle) { throw 'App still has active operations; no process was stopped' }
$pre = @{posts_total=@($posts).Count; render_active=$queue.active; render_running=$queue.running; content_running=$content.running; meta_publishing=$publishing.Count; scheduler_cycle_active=$scheduler.cycle_active; read_only_reconciliation_stop=$readOnlyReconciliationStop; checked_at=[DateTime]::Now.ToString('o')}
$pre | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'pre_install_snapshot.json') -Encoding UTF8
$render | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidence 'render_quiescence.json') -Encoding UTF8
InstallerMethod 'StopRunningApplication' @($target) | Out-Null
$remaining = @(Get-Process | Where-Object { $_.Path -and $_.Path.StartsWith($target + '\', [StringComparison]::OrdinalIgnoreCase) })
if ($remaining.Count) { throw 'Application processes remain; aborting extraction' }
$mutable = @{}
foreach ($file in Get-ChildItem -LiteralPath $target -File) {
    if (($file.Extension -eq '.json' -or $file.Name -eq 'posts.json.bak') -and $file.Name -ne 'build_identity.json') {
        if (InstallerMethod 'ShouldPreserve' @($file.Name)) { $mutable[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash }
    }
}
foreach ($directory in @('data','config')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $target $directory) -Recurse -File) {
        if ($directory -eq 'data' -or $file.Name -eq 'website_config.json') { $mutable[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash }
    }
}
InstallerMethod 'BackupMutableState' @($target) | Out-Null
$backup = Get-ChildItem -LiteralPath (Join-Path $target 'update_backups') -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $target 'data') -File -Filter '*.sqlite3*') {
    Copy-Item -LiteralPath $file.FullName -Destination (Join-Path $backup.FullName ('data\' + $file.Name))
}
$payload = $assembly.GetManifestResourceStream('HighlightDesktopTest.Payload')
$archive = [IO.Compression.ZipArchive]::new($payload, [IO.Compression.ZipArchiveMode]::Read, $false)
try {
    $progress = [Action[string,int]] { param($message, $percent) }
    InstallerMethod 'ExtractArchive' @($archive, $target, $progress) | Out-Null
} finally { $archive.Dispose(); $payload.Dispose() }
foreach ($path in $mutable.Keys) {
    if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ne $mutable[$path]) { throw "Installer changed mutable state: $path" }
}
foreach ($file in $verified.packaged_files) {
    if ((Get-FileHash -LiteralPath (Join-Path $target $file.file) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $file.sha256) { throw "Installed code mismatch: $($file.file)" }
}
$identity = Get-Content -LiteralPath (Join-Path $target 'build_identity.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($identity.app_version -ne '1.3.0') { throw 'Installed version mismatch' }
$report = @{installed=$true; installed_at=[DateTime]::Now.ToString('o'); target=$target; installer_sha256=$verified.sha256; preserved_file_count=$mutable.Count; pre_install=$pre; code_hashes_match=$true; code_files=$verified.packaged_files.Count; mutable_hashes_unchanged=$true; backup=$backup.FullName}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $evidence 'install_preservation.json') -Encoding UTF8
Start-Process -FilePath (Join-Path $target 'Highlight_Desktop_Test.exe') -WorkingDirectory $target -WindowStyle Hidden
$report | ConvertTo-Json -Depth 6
