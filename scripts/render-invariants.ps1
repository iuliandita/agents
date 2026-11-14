#!/usr/bin/env pwsh
# PowerShell launcher; mirror of scripts/render-invariants for native Windows.
$ErrorActionPreference = 'Stop'
$launcher = Get-Item -LiteralPath $PSCommandPath -Force
if ($launcher.LinkType -eq 'SymbolicLink') {
    $launcher = $launcher.ResolveLinkTarget($true)
}
$scriptDir = $launcher.DirectoryName
. "$scriptDir/python-runtime.ps1"

$root = Split-Path -Parent $scriptDir
$python = Get-AgentsPython $args
$prefix = @($python.Prefix)
& $python.Exe @prefix (Join-Path $root 'scripts/render_invariants.py') --repo-root $root @args
exit $LASTEXITCODE
