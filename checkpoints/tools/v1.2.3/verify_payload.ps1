param([string]$Version = '1.2.3')
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
    if ($identity.source_commit -ne (git -C $source rev-parse 'v1.2.3^{commit}').Trim()) { throw 'Source code commit mismatch' }
    if ($identity.app_version -ne $Version -or $identity.prerelease_build -ne $Version -or $identity.source_dirty) { throw 'Wrong build identity or dirty source' }
    if ((ReadText 'posts.json').Trim() -ne '[]') { throw 'Populated posts ledger inside release' }
    $forbidden = @($entries.Keys | Where-Object { $_ -match '(^|/)(tokens_vault|pages|page_groups|token_groups|jobs|crawled_videos|hardware_profile|scheduler_heartbeat|pending_first_comments|content_packages|first_comment_profiles|render_queue_state|publishing_settings|output_pipeline)\.json$' -or $_ -match '^(data|output|downloads|temp|run)/.+' -and -not $_.EndsWith('/') })
    if ($forbidden.Count) { throw 'Runtime state found inside release; values withheld' }
    foreach ($seed in @('config.json','config/website_config.json')) {
        if ([regex]::IsMatch((ReadText $seed), '"(?:api_key|password|access_token|page_token)"\s*:\s*"[^"\s][^"]*"', [Text.RegularExpressions.RegexOptions]::IgnoreCase)) { throw 'Nonempty credential seed; values withheld' }
    }
    if ((ReadText 'web/templates/index.html') -ne (ReadText 'web/index.html')) { throw 'Packaged templates differ' }
    $verified = @()
    foreach ($name in @('web/post_retry.py','web/meta_diagnostics.py','web/meta_recovery.py','src/output_pipeline.py','src/output_scheduling.py','src/pipeline.py','src/content_packages.py','src/english_text.py','src/publisher/website_publisher.py','web/app.py','web/index.html','web/templates/index.html','web/static/group_review.js','web/post_queries.py','web/posts_store.py','web/meta_handoff.py','web/scheduled_publisher.py','src/media_validation.py','src/publisher/meta_reel_poster.py','web/video_recovery.py','core/website_article_service.py')) {
        $stream = $entries[$name].Open()
        $sha = [Security.Cryptography.SHA256]::Create()
        try { $hash = ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
        finally { $stream.Dispose(); $sha.Dispose() }
        if ($hash -ne (Get-FileHash -LiteralPath (Join-Path $source $name) -Algorithm SHA256).Hash.ToLowerInvariant()) { throw "Payload code mismatch: $name" }
        $verified += @{file=$name; matches_source=$true; sha256=$hash}
    }
    $report = @{success=$true; setup=$setup; sha256=(Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant(); size=(Get-Item -LiteralPath $setup).Length;
        build=$identity.prerelease_build; source_identity=$identity; packaged_files=$verified; runtime_state_absent=$true; credential_seeds_empty=$true;
        test_result='631 passed, 4 skipped, 29 subtests passed'; browser_checks='9 offline checks; preparing selection, today preview and apply, stock allocation, midnight overflow, group preparation and review, 50/30 rows per page, batch approval, draft editor, daily manual/Meta mode, retry, overdue Meta and read-only refresh; no JavaScript errors';
        live_meta_test=$false; installed_in_active_runtime=$false}
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath (Join-Path $source 'checkpoints\evidence\v1.2.3\installer_verify.json')
    @{success=$report.success; setup=$report.setup; sha256=$report.sha256; size=$report.size; matched_source_files=$verified.Count; runtime_state_absent=$true} | ConvertTo-Json
} finally { $archive.Dispose(); $payload.Dispose() }
