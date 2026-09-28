param(
    [string]$Version = "1.0.19",
    [string]$BuildChannel = "desktop-test",
    [string]$ToolSource = "D:\Highlight_Video_Studio\bin",
    [string]$IconSource = "D:\Highlight_Video_Studio\app.ico",
    [string]$WhisperModelSource = "$env:USERPROFILE\.cache\huggingface\hub\models--Systran--faster-whisper-small"
)

$ErrorActionPreference = "Stop"
if ($BuildChannel -ne "desktop-test") { throw "Phase 1.5 permits only BUILD_CHANNEL=desktop-test" }
if ($Version -ne "1.0.19") { throw "Phase 1.5 test artifact must remain APP_VERSION=1.0.19" }

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $root "build\desktop-test-v$Version"
$stage = Join-Path $buildRoot "app"
$release = Join-Path $root "release"
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$pythonZip = Join-Path $buildRoot "python-3.11.7-embed-amd64.zip"
$payload = Join-Path $buildRoot "Highlight_Desktop_Test_Package_v$Version.zip"

if (-not (Test-Path -LiteralPath $csc)) { throw "C# compiler not found: $csc" }
if (-not (Test-Path -LiteralPath $IconSource)) { throw "Icon not found: $IconSource" }
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage, $release | Out-Null

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

$buildIdentity = @{
    app_version = $Version
    build_channel = $BuildChannel
    product_name = "Highlight Desktop Test"
    bind_host = "127.0.0.1"
    port = "ephemeral-loopback-never-5080"
    source_commit = (git -C $root rev-parse HEAD).Trim()
    built_at_utc = [DateTime]::UtcNow.ToString("o")
}
$buildIdentity | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage "build_identity.json") -Encoding UTF8

foreach ($tool in @("ffmpeg.exe", "ffprobe.exe", "node.exe", "yt-dlp.exe")) {
    $source = Join-Path $ToolSource $tool
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing binary: $source" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage "bin\$tool") -Force
}

$runtime = Join-Path $stage "runtime"
if (-not (Test-Path -LiteralPath $pythonZip)) {
    $oldZip = Join-Path $root "build\v$Version\python-3.11.7-embed-amd64.zip"
    if (Test-Path -LiteralPath $oldZip) { Copy-Item -LiteralPath $oldZip -Destination $pythonZip -Force }
    else { Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip" -OutFile $pythonZip }
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Expand-Archive -LiteralPath $pythonZip -DestinationPath $runtime -Force
$sitePackages = Join-Path $runtime "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
python -m pip --python (Join-Path $runtime "python.exe") install --disable-pip-version-check --no-compile --upgrade --target $sitePackages -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Portable runtime dependency install failed" }
Set-Content -LiteralPath (Join-Path $runtime "python311._pth") -Encoding ASCII -Value @("python311.zip", ".", "..", "Lib\site-packages", "import site")

if (-not (Test-Path -LiteralPath $WhisperModelSource)) { throw "Whisper model cache missing: $WhisperModelSource" }
$whisperTarget = Join-Path $stage "models\faster-whisper-small"
New-Item -ItemType Directory -Force -Path $whisperTarget | Out-Null
$snapshot = Get-ChildItem (Join-Path $WhisperModelSource "snapshots") -Directory | Select-Object -First 1
if (-not $snapshot) { throw "Whisper model cache has no snapshot" }
foreach ($modelFile in Get-ChildItem $snapshot.FullName -File) { Copy-Item -LiteralPath $modelFile.FullName -Destination (Join-Path $whisperTarget $modelFile.Name) -Force }

$launcherPath = Join-Path $stage "Highlight_Desktop_Test.exe"
& $csc /nologo /target:winexe /optimize+ ("/out:" + $launcherPath) ("/win32icon:" + (Join-Path $stage "app.ico")) /reference:System.dll /reference:System.Windows.Forms.dll (Join-Path $root "AppLauncher.cs")
if ($LASTEXITCODE -ne 0) { throw "Launcher compile failed" }

if (Test-Path -LiteralPath $payload) { Remove-Item -LiteralPath $payload -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $payload -CompressionLevel Optimal
$setup = Join-Path $release "Highlight_Desktop_Test_Setup_v$Version.exe"
& $csc /nologo /target:winexe /optimize+ ("/out:" + $setup) ("/win32icon:" + (Join-Path $stage "app.ico")) /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll /reference:Microsoft.CSharp.dll ("/resource:" + $payload + ",HighlightDesktopTest.Payload") (Join-Path $root "Installer.cs")
if ($LASTEXITCODE -ne 0) { throw "Installer compile failed" }

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLowerInvariant()
$hashFile = Join-Path $release "Highlight_Desktop_Test_Setup_v$Version.sha256"
Set-Content -LiteralPath $hashFile -Encoding ASCII -Value "$hash  Highlight_Desktop_Test_Setup_v$Version.exe"
Write-Host "Release built: $setup"
Write-Host "SHA256: $hash"
