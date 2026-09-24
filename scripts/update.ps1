#!/usr/bin/env pwsh
# PowerShell launcher; mirror of scripts/update for native Windows.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/python-runtime.ps1"

$root = Split-Path -Parent $PSScriptRoot
$python = Get-AgentsPython
$prefix = @($python.Prefix)
& $python.Exe @prefix (Join-Path $root 'scripts/update.py') --repo-root $root @args
exit $LASTEXITCODE
