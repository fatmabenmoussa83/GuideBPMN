$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvironmentDirectory = Join-Path $ProjectRoot "env"
$PythonExecutable = Join-Path $EnvironmentDirectory "Scripts\python.exe"

Write-Host "Creating the Python environment..." -ForegroundColor Cyan
if (-not (Test-Path $PythonExecutable)) {
    py -3.11 -m venv $EnvironmentDirectory
}

Write-Host "Installing project dependencies..." -ForegroundColor Cyan
& $PythonExecutable -m pip install --upgrade pip
& $PythonExecutable -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

& $PythonExecutable -m pip install -r (Join-Path $ProjectRoot "webapi\requirements-web.txt")

Write-Host "Setup completed." -ForegroundColor Green
Write-Host "Before running, define the API key of the LLM you use: $env:OPENAI_API_KEY (GPT-6 Luna) or $env:ANTHROPIC_API_KEY (Claude Haiku 5.5)."
Write-Host "Then execute: .\start_webapi.ps1"
