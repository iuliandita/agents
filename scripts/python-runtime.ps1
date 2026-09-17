# Sourced by the .ps1 launchers; mirrors scripts/python-runtime.sh.
# Selects AGENTS_PYTHON, then the checkout .venv, then python/python3 on PATH,
# then the Windows py launcher.

function Get-AgentsPython {
    $versionCheck = 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'

    if (Test-Path Env:AGENTS_PYTHON) {
        $override = $env:AGENTS_PYTHON
        if ($override) {
            & $override -c $versionCheck 2>$null
            if ($LASTEXITCODE -eq 0) { return [pscustomobject]@{ Exe = $override; Prefix = @() } }
        }
        throw 'AGENTS_PYTHON must name a working Python 3.11+ executable (not a command with flags). See INSTALL.md.'
    }

    $root = Split-Path -Parent $PSScriptRoot
    $venvCandidates = @(
        (Join-Path $root '.venv/Scripts/python.exe'),
        (Join-Path $root '.venv/bin/python')
    )
    foreach ($candidate in $venvCandidates) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -c $versionCheck 2>$null
            if ($LASTEXITCODE -eq 0) { return [pscustomobject]@{ Exe = $candidate; Prefix = @() } }
            throw 'The repository virtual environment python must be a working Python 3.11+ executable. Repair it or set AGENTS_PYTHON. See INSTALL.md.'
        }
    }

    foreach ($name in @('python', 'python3')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            & $command.Source -c $versionCheck 2>$null
            if ($LASTEXITCODE -eq 0) { return [pscustomobject]@{ Exe = $command.Source; Prefix = @() } }
        }
    }

    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -c $versionCheck 2>$null
        if ($LASTEXITCODE -eq 0) { return [pscustomobject]@{ Exe = $launcher.Source; Prefix = @('-3') } }
    }

    throw 'Python 3.11+ is required. Activate a supported virtual environment or set AGENTS_PYTHON. See INSTALL.md.'
}
