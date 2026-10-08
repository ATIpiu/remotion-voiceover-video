# Job runner: remote agents cannot type into terminals on this PC, so the user double-clicks
# start_runner.bat ONCE; afterwards the agent drops *.ps1 files into <Root>\jobs and they run in order.
param([string]$Root = (Split-Path -Parent $PSScriptRoot))
New-Item -ItemType Directory -Force "$Root\jobs\done", "$Root\logs" | Out-Null
$host.UI.RawUI.WindowTitle = "local-av job runner: $Root"
Write-Host "Job runner watching $Root\jobs (keep this window open)"
while ($true) {
  Get-ChildItem "$Root\jobs\*.ps1" -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
    $n = $_.Name
    "START $n $(Get-Date -f o)" | Out-File -Append -Encoding utf8 "$Root\logs\runner.txt"
    Move-Item $_.FullName "$Root\jobs\done\$n" -Force
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$Root\jobs\done\$n"
    "END $n $LASTEXITCODE $(Get-Date -f o)" | Out-File -Append -Encoding utf8 "$Root\logs\runner.txt"
  }
  Start-Sleep -Seconds 3
}
