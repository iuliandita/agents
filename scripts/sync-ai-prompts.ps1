#!/usr/bin/env pwsh
# PowerShell launcher; mirror of scripts/sync-ai-prompts for native Windows.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/python-runtime.ps1"

$root = Split-Path -Parent $PSScriptRoot
$python = Get-AgentsPython
$prefix = @($python.Prefix)
& $python.Exe @prefix (Join-Path $root 'scripts/render_prompts.py') --repo-root $root @args
exit $LASTEXITCODE
