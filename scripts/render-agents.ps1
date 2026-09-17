#!/usr/bin/env pwsh
# PowerShell launcher; mirror of scripts/render-agents for native Windows.
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/python-runtime.ps1"

$root = Split-Path -Parent $PSScriptRoot
$python = Get-AgentsPython
$prefix = @($python.Prefix)
& $python.Exe @prefix (Join-Path $root 'scripts/render_agents.py') --repo-root $root @args
exit $LASTEXITCODE
