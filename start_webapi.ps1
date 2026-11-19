# start_webapi.ps1 -- start the GuideBPMN API used by the website (docs/run.html).
# Usage, from the project root:  .\start_webapi.ps1            (http://127.0.0.1:8765)
#                                .\start_webapi.ps1 -Port 9000
param([int]$Port = 8765, [string]$BindHost = "127.0.0.1", [string]$Catalogue = "")
# -Catalogue (optional): force one learned-guidelines file for this API. Without it, every run
# uses the catalogue of its generator model (guidelines\learned\<model>\), chosen automatically.
if ($Catalogue) { $env:GUIDEBPMN_CATALOGUE = $Catalogue } else { Remove-Item Env:\GUIDEBPMN_CATALOGUE -ErrorAction SilentlyContinue }
Set-Location $PSScriptRoot
$py = if (Test-Path ".\env\Scripts\python.exe") { ".\env\Scripts\python.exe" } else { "python" }
& $py -c "import fastapi, uvicorn, multipart" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing the web API requirements (once)..." -ForegroundColor Cyan
    & $py -m pip install -r webapi\requirements-web.txt
}
if (-not $env:OPENAI_API_KEY -and -not $env:ANTHROPIC_API_KEY) { Write-Host "Note: no API key is set in this terminal (OPENAI_API_KEY for GPT-6 Luna, ANTHROPIC_API_KEY for Claude Haiku 5.5): only dry runs can start." -ForegroundColor Yellow }
if ($Catalogue) { Write-Host "Learned catalogue (forced): $Catalogue" -ForegroundColor Green } else { Write-Host "Learned catalogue: one per generator model, under guidelines\learned\" -ForegroundColor Green }
Write-Host "GuideBPMN API on http://$($BindHost):$Port  (interactive docs: http://$($BindHost):$Port/docs)" -ForegroundColor Green
Write-Host "Open docs\run.html (or the GitHub Pages site), page Run GuideBPMN. Ctrl+C to stop." -ForegroundColor Green
& $py -m uvicorn webapi.app:app --host $BindHost --port $Port
