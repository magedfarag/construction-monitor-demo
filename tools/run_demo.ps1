# Ensure Cargo is on PATH (needed to build pydantic-core from source on Python 3.14)
$cargoBin = "$env:USERPROFILE\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin"
if ((Test-Path $cargoBin) -and ($env:PATH -notlike "*$cargoBin*")) {
    $env:PATH = "$cargoBin;$env:PATH"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    python -m venv $venvDir
}

& $venvPython -m pip install -r (Join-Path $repoRoot "requirements.txt")
& $venvPython -m uvicorn app.main:app --reload
