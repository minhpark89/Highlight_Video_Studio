param(
    [string]$Version = "1.0.12",
    [string]$ToolSource = "E:\OPENCLAW\BOB\Highlight_Studio_Setup.exe v1.0.8\bin",
    [string]$IconSource = "E:\OPENCLAW\BOB\Highlight_Studio_Setup.exe v1.0.8\app.ico"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $root "build\v$Version"
$stage = Join-Path $buildRoot "app"
$release = Join-Path $root "release"
$csc = "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$pythonZip = Join-Path $buildRoot "python-3.11.7-embed-amd64.zip"
$payload = Join-Path $buildRoot "Highlight_Studio_Package_v$Version.zip"

if (-not (Test-Path -LiteralPath $csc)) { throw "Không tìm thấy C# compiler: $csc" }
if (-not (Test-Path -LiteralPath $IconSource)) { throw "Không tìm thấy app.ico: $IconSource" }
New-Item -ItemType Directory -Force -Path $stage, $release | Out-Null

$sourceDirs = @("core", "src", "web", "research")
foreach ($name in $sourceDirs) {
    $target = Join-Path $stage $name
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    robocopy (Join-Path $root $name) $target /E /NFL /NDL /NJH /NJS /NC /NS /XD __pycache__ /XF "*.pyc" "*.bak" "*.bak*" | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "Không thể copy $name (robocopy $LASTEXITCODE)" }
}

New-Item -ItemType Directory -Force -Path (Join-Path $stage "config"), (Join-Path $stage "data"), (Join-Path $stage "downloads"), (Join-Path $stage "output"), (Join-Path $stage "temp"), (Join-Path $stage "bin") | Out-Null
Copy-Item -LiteralPath (Join-Path $root "config.json"), (Join-Path $root "posts.json"), (Join-Path $root "run_server.py"), (Join-Path $root "requirements.txt") -Destination $stage -Force
Copy-Item -LiteralPath (Join-Path $root "config\website_config.json") -Destination (Join-Path $stage "config\website_config.json") -Force
Copy-Item -LiteralPath $IconSource -Destination (Join-Path $stage "app.ico") -Force

foreach ($tool in @("ffmpeg.exe", "ffprobe.exe", "node.exe", "yt-dlp.exe")) {
    $source = Join-Path $ToolSource $tool
    if (-not (Test-Path -LiteralPath $source)) { throw "Thiếu binary: $source" }
    Copy-Item -LiteralPath $source -Destination (Join-Path $stage "bin\$tool") -Force
}

$runtime = Join-Path $stage "runtime"
if (-not (Test-Path -LiteralPath $pythonZip)) {
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-embed-amd64.zip" -OutFile $pythonZip
}
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
Expand-Archive -LiteralPath $pythonZip -DestinationPath $runtime -Force
$sitePackages = Join-Path $runtime "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null
python -m pip install --disable-pip-version-check --no-compile --upgrade --target $sitePackages -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "pip install runtime thất bại" }
Set-Content -LiteralPath (Join-Path $runtime "python311._pth") -Encoding ASCII -Value @("python311.zip", ".", "..", "Lib\site-packages", "import site")

$launcherOut = "/out:" + (Join-Path $stage "Highlight_Studio.exe")
$launcherIcon = "/win32icon:" + (Join-Path $stage "app.ico")
& $csc /nologo /target:winexe /optimize+ $launcherOut $launcherIcon /reference:System.dll /reference:System.Windows.Forms.dll (Join-Path $root "AppLauncher.cs")
if ($LASTEXITCODE -ne 0) { throw "Compile launcher thất bại" }

if (Test-Path -LiteralPath $payload) { Remove-Item -LiteralPath $payload -Force }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $payload -CompressionLevel Optimal
$setup = Join-Path $release "Highlight_Studio_Setup_v$Version.exe"
$setupOut = "/out:" + $setup
$setupIcon = "/win32icon:" + (Join-Path $stage "app.ico")
$payloadResource = "/resource:" + $payload + ",HighlightStudio.Payload"
& $csc /nologo /target:winexe /optimize+ $setupOut $setupIcon /reference:System.dll /reference:System.Drawing.dll /reference:System.Windows.Forms.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll /reference:Microsoft.CSharp.dll $payloadResource (Join-Path $root "Installer.cs")
if ($LASTEXITCODE -ne 0) { throw "Compile installer thất bại" }

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $setup).Hash.ToLowerInvariant()
Set-Content -LiteralPath (Join-Path $release "Highlight_Studio_Setup_v$Version.sha256") -Encoding ASCII -Value "$hash  Highlight_Studio_Setup_v$Version.exe"
Write-Host "Release built: $setup"
Write-Host "SHA256: $hash"
