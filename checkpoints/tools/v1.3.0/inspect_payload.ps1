param([string]$Version = '1.3.0')
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$setup = Join-Path $source "release\Highlight_Desktop_Test_Setup_v$Version.exe"
$evidenceDir = Join-Path $source "checkpoints\evidence\v$Version"
$tests = Get-Content -Encoding UTF8 -LiteralPath (Join-Path $evidenceDir 'offline_tests.json') -Raw | ConvertFrom-Json
$javascript = Get-Content -Encoding UTF8 -LiteralPath (Join-Path $evidenceDir 'javascript_syntax.json') -Raw | ConvertFrom-Json
$browser = Get-Content -Encoding UTF8 -LiteralPath (Join-Path $evidenceDir 'offline_ui.json') -Raw | ConvertFrom-Json
if (-not $tests.success -or -not $javascript.success -or -not $browser.success) { throw 'Offline verification evidence unsuccessful' }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.IO.Compression
$assembly = [Reflection.Assembly]::LoadFile($setup)
$payload = $assembly.GetManifestResourceStream('HighlightDesktopTest.Payload')
if ($null -eq $payload) { throw 'Missing installer payload' }
$archive = [IO.Compression.ZipArchive]::new($payload, [IO.Compression.ZipArchiveMode]::Read, $false)
try {
    $entries = @{}
    foreach ($entry in $archive.Entries) { $entries[($entry.FullName.Replace('\','/') -replace '^[./]+','')] = $entry }
    function ReadText([string]$Name) {
        $reader = [IO.StreamReader]::new($entries[$Name].Open(), [Text.Encoding]::UTF8)
        try { return $reader.ReadToEnd() } finally { $reader.Dispose() }
    }
    $identity = (ReadText 'build_identity.json') | ConvertFrom-Json
    if ($identity.source_commit -ne (git -C $source rev-parse HEAD).Trim()) { throw 'Packaged source base commit mismatch' }
    if ($identity.app_version -ne $Version -or $identity.prerelease_build -ne $Version) { throw 'Wrong build identity' }
    if ($identity.meta_graph_api_version -ne 'v24.0') { throw 'Wrong packaged Meta API version' }
    if ((ReadText 'posts.json').Trim() -ne '[]') { throw 'Populated posts ledger inside package' }
    $forbidden = @($entries.Keys | Where-Object {
        $_ -match '(^|/)(tokens_vault|pages|page_groups|token_groups|jobs|crawled_videos|hardware_profile|scheduler_heartbeat|pending_first_comments|content_packages|first_comment_profiles|render_queue_state|publishing_settings|output_pipeline)\.json$' -or
        ($_ -match '^(data|output|downloads|temp|run)/.+' -and -not $_.EndsWith('/'))
    })
    if ($forbidden.Count) { throw 'Runtime state found inside package; values withheld' }
    foreach ($seed in @('config.json','config/website_config.json')) {
        if ([regex]::IsMatch((ReadText $seed), '"(?:api_key|password|access_token|page_token)"\s*:\s*"[^"\s][^"]*"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)) { throw 'Nonempty credential seed; values withheld' }
    }
    if ((ReadText 'web/templates/index.html') -ne (ReadText 'web/index.html')) { throw 'Packaged templates differ' }
    if (-not (ReadText 'web/app.py').Contains("APP_VERSION = `"$Version`"")) { throw 'Packaged app version mismatch' }
    $verified = @()
    $sourceFiles = @($entries.Keys | Where-Object { $_ -match '^(core|src|web|multi_pc|research)/.+\.(py|html|js|css|ttf)$' })
    $sourceFiles += @('web/static/fonts/provenance.json','web/static/fonts/anton-OFL.txt',
        'web/static/fonts/barlowcondensed-OFL.txt','web/static/fonts/bevietnampro-OFL.txt')
    foreach ($name in $sourceFiles) {
        $stream = $entries[$name].Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $stream.Dispose(); $sha.Dispose() }
        if ($hash -ne (Get-FileHash -LiteralPath (Join-Path $source $name) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Payload code mismatch: $name" }
        $verified += @{file=$name; matches_source=$true; sha256=$hash}
    }
    foreach ($required in @('src/job_store.py','src/job_checkpoints.py','src/media_quality_gate.py',
        'src/media_download.py','src/download_process.py','src/long_transcription.py','src/render_quality.py',
        'web/post_lineage.py','core/article_quality.py','src/caption_timing.py','src/captions.py',
        'web/recovery_requests.py','web/recovery_content.py','web/queue_readiness.py',
        'web/static/recovery_tracking.js','web/static/posts_interactions.js',
        'web/static/scheduler_feedback.js','web/static/posts_interactions.css',
        'web/static/fonts/Anton-Regular.ttf','web/static/fonts/BarlowCondensed-Black.ttf','web/static/fonts/BeVietnamPro-ExtraBold.ttf')) {
        if (-not $entries.ContainsKey($required)) { throw "Missing new package file: $required" }
    }
    $hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    $checksum = (Get-Content -LiteralPath (Join-Path $source "release\Highlight_Desktop_Test_Setup_v$Version.sha256") -Raw).Split(' ')[0].Trim()
    if ($checksum -ne $hash) { throw 'Installer checksum mismatch' }
    $report = @{success=$true; setup=$setup; sha256=$hash; size=(Get-Item -LiteralPath $setup).Length;
        source_identity=$identity; packaged_files=$verified; runtime_state_absent=$true; credential_seeds_empty=$true;
        meta_graph_api_version='v24.0'; offline_test_summary=$tests.summary; javascript_syntax_verified=$true;
        browser_checks=$browser.checks; local_build_only=$true; published=$false; installed_in_active_runtime=$false}
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidenceDir 'installer_payload.json')
    @{success=$true; setup=$setup; sha256=$hash; size=$report.size; matched_source_files=$verified.Count;
        local_build_only=$true; source_dirty=$identity.source_dirty; runtime_state_absent=$true} | ConvertTo-Json
}
finally { $archive.Dispose(); $payload.Dispose() }
