$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
Push-Location $sourceRoot
try {
    & python (Join-Path $PSScriptRoot 'github_release.py') deploy
    if ($LASTEXITCODE -ne 0) { throw 'Deployment stopped; no success claimed. Read the sanitized error and deployment checkpoint.' }
}
finally { Pop-Location }
