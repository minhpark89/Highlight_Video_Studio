param(
    [string]$Version = "1.3.1",
    [string]$PreviewRevision = "",
    [string]$BuildChannel = "desktop-test",
    [switch]$SkipTests,
    [string]$ToolSource = "D:\Highlight_Video_Studio\bin",
    [string]$RuntimeSource = "",
    [string]$IconSource = "$(Join-Path $PSScriptRoot 'assets\highlight.ico')",
    [string]$WhisperModelSource = "$env:USERPROFILE\.cache\huggingface\hub\models--Systran--faster-whisper-small"
)

$ErrorActionPreference = "Stop"
if ($BuildChannel -ne "desktop-test") { throw "Phase 1.5 permits only BUILD_CHANNEL=desktop-test" }
$supportedVersions = @(
    "1.0.19", "1.1.6", "1.1.7", "1.1.8", "1.1.9", "1.2.0", "1.2.1", "1.2.2",
    "1.2.3", "1.2.4", "1.2.5", "1.2.6", "1.2.7", "1.2.8", "1.2.9", "1.2.10", "1.2.11", "1.3.0", "1.3.1"
)
if ($Version -notin $supportedVersions) { throw "Unsupported desktop-test APP_VERSION: $Version" }
if ($Version -eq "1.0.19" -and -not $PreviewRevision) { throw "Legacy v1.0.19 builds require PreviewRevision" }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $root "build\desktop-test-v$Version"
$stage = Join-Path $buildRoot ("stage-" + [Guid]::NewGuid().ToString("N"))
$release = Join-Path $root "release"
$releaseLabel = if ($PreviewRevision) { "$Version-$PreviewRevision" } else { $Version }
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$pythonZip = Join-Path $buildRoot "python-3.11.7-embed-amd64.zip"
$payload = Join-Path $buildRoot ("Highlight_Desktop_Test_Package_v$Version-" + [Guid]::NewGuid().ToString("N") + ".zip")

function Assert-BuildCleanupPath([string]$TargetPath) {
    $absoluteTarget = [IO.Path]::GetFullPath($TargetPath)
    $buildBoundary = [IO.Path]::GetFullPath($buildRoot).TrimEnd('\') + '\'
    if (-not $absoluteTarget.StartsWith($buildBoundary, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe build cleanup target: $absoluteTarget"
    }
}

if (-not (Test-Path -LiteralPath $csc)) { throw "C# compiler not found: $csc" }
if (-not (Test-Path -LiteralPath $ToolSource)) { throw "Tool source folder not found: $ToolSource" }
$ToolSource = (Resolve-Path -LiteralPath $ToolSource).Path
foreach ($tool in @("ffmpeg.exe", "ffprobe.exe", "node.exe", "yt-dlp.exe")) {
    if (-not (Test-Path -LiteralPath (Join-Path $ToolSource $tool))) {
        throw "Missing binary in tool source: $tool"
    }
}

$testPath = $env:PATH
$env:PATH = "$ToolSource;$testPath"
try {
    if (-not $SkipTests) {
        Push-Location $root
        try {
            $testGroups = @(
            @("tests/test_multi_pc_hardware.py", "tests/test_multi_pc_local_mvp.py", "tests/test_multi_pc_phase1.py"),
            ,@("tests/test_release_guards.py"),
            @("tests/test_page_token_sync.py", "tests/test_parallel_publishing.py", "tests/test_posting_schedule.py"),
            @("tests/test_youtube_embed_publish.py", "tests/test_scheduling_publish_flow.py"),
            @("tests/test_meta_native_handoff.py", "tests/test_meta_queue_handoff.py", "tests/test_meta_scheduling_profiles.py", "tests/test_fallback_comments.py", "tests/test_preview26_source_metadata.py", "tests/test_preview28_long_article_fallback.py"),
            @("tests/test_first_comment_audit.py", "tests/test_whisper_lazy_fallback.py", "tests/test_installer_data_preservation.py", "tests/test_preview23_image_sources.py"),
            @("tests/test_content_studio_pipeline.py", "tests/test_website_ui_regression.py", "tests/test_output_pipeline.py"),
            @("tests/test_video_recovery.py", "tests/test_website_repair.py", "tests/test_english_public_content.py", "tests/test_group_review.py", "tests/test_schedule_today.py"),
            @("tests/test_post_retry.py", "tests/test_meta_credential_recovery.py"),
            ,@("tests/test_v129_website_captions_recovery.py"),
            ,@("tests/test_v1210_queue_recovery.py"),
            ,@("tests/test_v130_desktop_recovery_and_schedule.py")
        )
            foreach ($group in $testGroups) {
                & python -m pytest @group -q --no-header
                if ($LASTEXITCODE -ne 0) { throw "Release tests failed (pytest $LASTEXITCODE); use -SkipTests only to debug" }
            }
        }
        finally { Pop-Location }
    }
}
finally {
    $env:PATH = $testPath
}
if (-not (Test-Path -LiteralPath $IconSource)) { throw "Icon not found: $IconSource" }
New-Item -ItemType Directory -Force -Path $stage, $release | Out-Null

# A unique stage prevents stale preview processes from locking or corrupting a rebuild.
$stageRuntime = Join-Path $stage "runtime"
$lockedRuntime = Join-Path $root "build\desktop-test-v$Version\runtime-locked"
$expectedRequirements = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root "requirements.txt")).Hash.ToLowerInvariant()
$cachedLockPath = Join-Path $lockedRuntime "requirements.lock.txt"
$cachedLockMatches = (Test-Path -LiteralPath $cachedLockPath) -and ((Get-Content -LiteralPath $cachedLockPath -Raw).Contains("requirements=$expectedRequirements"))
if ($cachedLockMatches) {
    Copy-Item -LiteralPath $lockedRuntime -Destination $stageRuntime -Recurse -Force
    Write-Host "Reusing locked embedded runtime: $lockedRuntime"
}
elseif ($RuntimeSource) {
    $sourceRuntime = (Resolve-Path -LiteralPath $RuntimeSource).Path
    $lockText = Get-Content -LiteralPath (Join-Path $sourceRuntime "requirements.lock.txt") -Raw
    if (-not $lockText.Contains("requirements=$expectedRequirements")) { throw "RuntimeSource lock does not match requirements.txt" }
    Copy-Item -LiteralPath $sourceRuntime -Destination $stageRuntime -Recurse -Force
    Write-Host "Using verified embedded runtime: $sourceRuntime"
}

$sourceDirs = @("core", "src", "web", "research", "multi_pc")
foreach ($name in $sourceDirs) {
    $target = Join-Path $stage $name
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    robocopy (Join-Path $root $name) $target /E /NFL /NDL /NJH /NJS /NC /NS /XD __pycache__ /XF "*.pyc" "*.bak" "*.bak*" | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Cannot copy $name (robocopy $LASTEXITCODE)" }
}

New-Item -ItemType Directory -Force -Path (Join-Path $stage "config"), (Join-Path $stage "data"), (Join-Path $stage "downloads"), (Join-Path $stage "output"), (Join-Path $stage "temp"), (Join-Path $stage "bin") | Out-Null
Copy-Item -LiteralPath (Join-Path $root "config.json"), (Join-Path $root "posts.json"), (Join-Path $root "run_server.py"), (Join-Path $root "requirements.txt") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $root "config\website_config.json") -Destination (Join-Path $stage "config\website_config.json") -Force
Copy-Item -LiteralPath $IconSource -Destination (Join-Path $stage "app.ico") -Force

$metaApiVersion = (& python -c "import sys; sys.path.insert(0, sys.argv[1]); from src.publisher.meta_api import GRAPH_API_VERSION; print(GRAPH_API_VERSION)" $root).Trim()
if ($LASTEXITCODE -ne 0 -or -not $metaApiVersion) { throw "Cannot read Meta Graph API build version" }
$buildIdentity = @{
    app_version = $Version
    prerelease_build = $releaseLabel
    build_channel = $BuildChannel
    product_name = "Highlight Desktop Test"
    meta_graph_api_version = $metaApiVersion
    bind_host = "127.0.0.1"
    port = "ephemeral-loopback-never-5080"
    source_commit = (git -C $root rev-parse HEAD).Trim()
    source_dirty = [bool](git -C $root status --porcelain --untracked-files=normal)
    built_at_utc = [DateTime]::UtcNow.ToString("o")
}
$buildIdentity | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage "build_identity.json") -Encoding UTF8

foreach ($tool in @("ffmpeg.exe", "ffprobe.exe", "node.exe", "yt-dlp.exe")) {
    $source = Join-Path $ToolSource $tool
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing binary: $source" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage "bin\$tool") -Force
}

$runtimeDir = Join-Path $stage "runtime"
$runtimeLock = Join-Path $runtimeDir "requirements.lock.txt"
if (Test-Path -LiteralPath $runtimeLock) {
    Write-Host "Locked embedded runtime already staged"
}
else {
    if (-not (Test-Path -LiteralPath $pythonZip)) {
        $oldZip = Join-Path $root "build\v$Version\python-3.11.7-embed-amd64.zip"
        if (Test-Path -LiteralPath $oldZip) { Copy-Item -LiteralPath $oldZip -Destination $pythonZip -Force }
        else { Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip" -OutFile $pythonZip }
    }
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    Expand-Archive -LiteralPath $pythonZip -DestinationPath $runtimeDir -Force
    $sitePackages = Join-Path $runtimeDir "Lib\site-packages"
    New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
    python -m pip --python (Join-Path $runtimeDir "python.exe") install --disable-pip-version-check --no-compile --upgrade --target $sitePackages -r (Join-Path $root "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Portable runtime dependency install failed" }
    Set-Content -LiteralPath (Join-Path $runtimeDir "python311._pth") -Encoding ASCII -Value @("python311.zip", ".", "..", "Lib\site-packages", "import site")
    Set-Content -LiteralPath $runtimeLock -Encoding ASCII -Value "python=3.11.7`nrequirements=$((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'requirements.txt')).Hash.ToLowerInvariant())"
    if (Test-Path -LiteralPath $lockedRuntime) {
        Assert-BuildCleanupPath $lockedRuntime
        Remove-Item -LiteralPath $lockedRuntime -Recurse -Force
    }
    Copy-Item -LiteralPath $runtimeDir -Destination $lockedRuntime -Recurse -Force
}

if (-not (Test-Path -LiteralPath $WhisperModelSource)) { throw "Whisper model source missing: $WhisperModelSource" }
$whisperTarget = Join-Path $stage "models\faster-whisper-small"
New-Item -ItemType Directory -Force -Path $whisperTarget | Out-Null
$modelSourceDir = if (Test-Path -LiteralPath (Join-Path $WhisperModelSource "model.bin")) { $WhisperModelSource } else {
    $snapshot = Get-ChildItem (Join-Path $WhisperModelSource "snapshots") -Directory | Select-Object -First 1
    if (-not $snapshot) { throw "Whisper model cache has no snapshot" }
    $snapshot.FullName
}
foreach ($modelFile in Get-ChildItem -LiteralPath $modelSourceDir -File) {
    $modelTarget = if ($modelFile.Target) { $modelFile.Target[0] } else { $modelFile.FullName }
    Copy-Item -LiteralPath $modelTarget -Destination (Join-Path $whisperTarget $modelFile.Name) -Force
    if ((Get-Item -LiteralPath (Join-Path $whisperTarget $modelFile.Name)).Length -ne (Get-Item -LiteralPath $modelTarget).Length) { throw "Whisper model copy incomplete: $($modelFile.Name)" }
}

$launcherPath = Join-Path $stage "Highlight_Desktop_Test.exe"
& $csc /nologo /target:winexe /optimize+ ("/out:" + $launcherPath) ("/win32icon:" + (Join-Path $stage "app.ico")) /reference:System.dll /reference:System.Windows.Forms.dll (Join-Path $root "AppLauncher.cs")
if ($LASTEXITCODE -ne 0) { throw "Launcher compile failed" }

# Stage must be complete before packaging: a partial runtime inside the installer
# would install a broken app, so fail loudly here instead.
$stagedRuntime = Join-Path $stage "runtime\python.exe"
if (-not (Test-Path -LiteralPath $stagedRuntime)) { throw "Staged runtime missing python.exe" }
foreach ($required in @("runtime\Lib\site-packages\flask", "runtime\Lib\site-packages\waitress", "runtime\Lib\site-packages\faster_whisper", "runtime\Lib\site-packages\tqdm", "bin\ffmpeg.exe", "bin\ffprobe.exe", "models\faster-whisper-small\model.bin")) {
    if (-not (Test-Path -LiteralPath (Join-Path $stage $required))) { throw "Staged package incomplete, missing: $required" }
}
& $stagedRuntime -c "import langdetect; from src.english_text import assert_english; assert_english('Watch the original video for full context.')"
if ($LASTEXITCODE -ne 0) { throw "English validation dependency missing from embedded runtime" }

# Fail-closed packaging guard: a public release must never ship this machine's
# hardware identity, per-user state, or runtime/local-environment files. Scan the
# staged tree before packaging and abort on any hit.
$forbiddenDirPrefixes = @("data\", "output\", "temp\", "downloads\", "logs\", "chrome_profile\", "artifacts\", "build\")
foreach ($dir in @("data", "output", "temp", "downloads")) {
    $dirPath = Join-Path $stage $dir
    if (Test-Path -LiteralPath $dirPath) {
        $stray = Get-ChildItem -LiteralPath $dirPath -Recurse -File -Force -ErrorAction SilentlyContinue
        if ($stray) { throw "Packaging guard: runtime/user state found under $dir\: $($stray[0].FullName)" }
    }
}
$forbiddenFileNames = @("hardware_profile.json", "scheduler_heartbeat.json", "tokens_vault.json", "pages.json", "page_groups.json", "crawled_videos.json", "schedule_rules.json", ".env")
$identityNeedles = @("RTX 3060", "GeForce", "Xeon", "E5-2680", "DESKTOP-COM8UQ7")
$scanExtensions = @(".py", ".html", ".htm", ".js", ".json", ".css", ".txt", ".md", ".cs", ".ps1", ".cfg", ".ini", ".yml", ".yaml")
$scanRoots = @("web", "src", "core", "multi_pc", "research", "config")
$guardHits = New-Object System.Collections.Generic.List[string]
foreach ($fname in $forbiddenFileNames) {
    $hits = Get-ChildItem -LiteralPath $stage -Recurse -File -Force -Filter $fname -ErrorAction SilentlyContinue
    foreach ($h in $hits) { $guardHits.Add("forbidden file: $($h.FullName.Substring($stage.Length))") }
}
foreach ($relRoot in $scanRoots) {
    $absRoot = Join-Path $stage $relRoot
    if (-not (Test-Path -LiteralPath $absRoot)) { continue }
    foreach ($file in Get-ChildItem -LiteralPath $absRoot -Recurse -File -Force -ErrorAction SilentlyContinue) {
        if ($file.FullName -match "-preview\." -or $file.FullName -match "\.bak") { continue }
        if ($scanExtensions -notcontains $file.Extension.ToLowerInvariant()) { continue }
        $text = Get-Content -LiteralPath $file.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($null -eq $text) { continue }
        foreach ($needle in $identityNeedles) {
            if ($text.Contains($needle)) { $guardHits.Add("hardware identity '$needle' in $($file.FullName.Substring($stage.Length))") }
        }
    }
}
if ($guardHits.Count -gt 0) {
    $guardHits | Select-Object -First 20 | ForEach-Object { Write-Host "  GUARD: $_" }
    throw "Packaging guard failed: $($guardHits.Count) unsafe entr(ies) in staged payload"
}
Write-Host "Packaging guard: staged tree clean (no runtime state, no machine identity)"


# Compress-Archive aborts on this tree (long paths / large payload), so use bsdtar,
# which produces a plain .zip the Installer reads via System.IO.Compression.
tar -a -c -f $payload -C $stage .
if ($LASTEXITCODE -ne 0) { throw "Payload zip failed (tar $LASTEXITCODE)" }
if (-not (Test-Path -LiteralPath $payload)) { throw "Payload zip missing: $payload" }
$setupName = "Highlight_Desktop_Test_Setup_v$releaseLabel.exe"
$setup = Join-Path $release $setupName
& $csc /nologo /target:winexe /optimize+ ("/out:" + $setup) ("/win32icon:" + (Join-Path $stage "app.ico")) /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll /reference:Microsoft.CSharp.dll ("/resource:" + $payload + ",HighlightDesktopTest.Payload") (Join-Path $root "Installer.cs")
if ($LASTEXITCODE -ne 0) { throw "Installer compile failed" }

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLowerInvariant()
$hashFile = Join-Path $release "Highlight_Desktop_Test_Setup_v$releaseLabel.sha256"
Set-Content -LiteralPath $hashFile -Encoding ASCII -Value "$hash  $setupName"
try { Remove-Item -LiteralPath $payload -Force -ErrorAction Stop } catch { Write-Warning "Could not remove temporary payload: $payload" }
try {
    Assert-BuildCleanupPath $stage
    Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction Stop
} catch { Write-Warning "Could not remove temporary stage: $stage" }
Write-Host "Release built: $setup"
Write-Host "SHA256: $hash"

