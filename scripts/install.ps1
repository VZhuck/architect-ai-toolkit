[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$RepoRawBase = "https://raw.githubusercontent.com/VZhuck/architect-ai-toolkit/main"
$ConfigFile = "ossify-cogents.json"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "'uv' is required but was not found on PATH. Install it from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

if (-not (Get-Command ossify-cogents -ErrorAction SilentlyContinue)) {
    Write-Host "ossify-cogents not found, installing via uv tool install..."
    uv tool install git+https://github.com/VZhuck/ossify-cogents.git
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ((Test-Path $ConfigFile) -and (-not $Force)) {
    Write-Error "'$ConfigFile' already exists in the current directory. Rerun with -Force to overwrite it."
    exit 1
}

Write-Host "Fetching $ConfigFile from architect-ai-toolkit (main)..."
Invoke-WebRequest -Uri "$RepoRawBase/$ConfigFile" -OutFile $ConfigFile -UseBasicParsing

Write-Host "Running ossify-cogents install..."
ossify-cogents install
exit $LASTEXITCODE
