param([string]$Version = '1.2.4')
$ErrorActionPreference = 'Stop'
$source = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$setup = Join-Path $source "release\Highlight_Desktop_Test_Setup_v$Version.exe"
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
    if ($identity.source_commit -ne (git -C $source rev-parse "v$Version^{commit}").Trim()) { throw 'Packaged source commit mismatch' }
    if ($identity.app_version -ne $Version -or $identity.prerelease_build -ne $Version -or $identity.source_dirty) { throw 'Wrong build identity or dirty source' }
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
    $verified = @()
    foreach ($name in @('src/publisher/meta_api.py','src/publisher/meta_reel_poster.py','src/publisher/token_vault.py','src/publisher/meta_preflight.py','src/publisher/page_manager.py','src/publisher/first_comment_queue.py','src/output_pipeline.py','src/output_scheduling.py','src/content_packages.py','web/app.py','web/page_insights.py','web/index.html','web/templates/index.html','web/full_script.js','web/meta_handoff.py','web/scheduled_publisher.py','web/meta_recovery.py','web/meta_diagnostics.py','web/posts_store.py')) {
        $stream = $entries[$name].Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $stream.Dispose(); $sha.Dispose() }
        if ($hash -ne (Get-FileHash -LiteralPath (Join-Path $source $name) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Payload code mismatch: $name" }
        $verified += @{file=$name; matches_source=$true; sha256=$hash}
    }
    $legacyReferences = @()
    foreach ($name in $entries.Keys) {
        if ($name -match '^(src|web|core|multi_pc|research)/.+\.(py|html|js)$' -and (ReadText $name).Contains('v22.0')) {
            $legacyReferences += $name
        }
    }
    if ($legacyReferences.Count) { throw ('Packaged production code still references v22.0: ' + ($legacyReferences -join ', ')) }
    $report = @{success=$true; setup=$setup; sha256=(Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant(); size=(Get-Item -LiteralPath $setup).Length;
        source_identity=$identity; packaged_files=$verified; runtime_state_absent=$true; credential_seeds_empty=$true;
        meta_graph_api_version='v24.0'; legacy_v22_references_absent=$true;
        regression_tests_run=$false; application_started=$false; live_meta_publish_test=$false; installed_in_active_runtime=$false}
    $evidenceDir = Join-Path $source "checkpoints\evidence\v$Version"
    New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $evidenceDir 'installer_payload.json')
    @{success=$true; setup=$setup; sha256=$report.sha256; size=$report.size; matched_source_files=$verified.Count; meta_graph_api_version='v24.0'; runtime_state_absent=$true; regression_tests_run=$false} | ConvertTo-Json
}
finally { $archive.Dispose(); $payload.Dispose() }
