# scripts/schedule_daily.ps1 - registers `sotawhat run daily` in Windows Task Scheduler (SDD 6.12, 8.3).
# Usage, from the repository root in PowerShell:
#   .\scripts\schedule_daily.ps1                         # 07:00
#   .\scripts\schedule_daily.ps1 -Listener               # also: Telegram feedback listener at logon (P1)
#   .\scripts\schedule_daily.ps1 -Web                    # also: graph interface at logon (P3)
#   .\scripts\schedule_daily.ps1 -Weekly                 # also: weekly report and ideas, Sundays 20:00 (P4)
# Runs as the current user while logged on; a missed run starts as soon as possible (StartWhenAvailable).
param(
    [string]$Time = "07:00",
    [string]$TaskName = "sotawhat-daily",
    [switch]$Listener,
    [switch]$Web,
    [switch]$Weekly,
    [string]$WeeklyTime = "20:00"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
$exe = Join-Path $repo ".venv\Scripts\sotawhat.exe"
if (-not (Test-Path $exe)) { throw "Not found: $exe - install first: uv pip install -e .[dev]" }
if (-not (Test-Path (Join-Path $repo ".env"))) { Write-Warning "No .env in $repo - copy .env.example to .env and fill it in." }

$arguments = "run daily"

# WorkingDirectory = repo root, so the `.env` file, `config\` and `data\insight.db` are found.
$action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "sotawhat 3.0 - coleta diaria + resumo no Telegram" -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State

if ($Listener) {
    # Votes on the Telegram buttons are acknowledged within seconds instead of at the next daily run.
    # pythonw.exe has no console window; output goes to data\logs. Restarts if it crashes.
    $pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path $pythonw)) { throw "Not found: $pythonw" }
    $listen = New-ScheduledTaskAction -Execute $pythonw -Argument "-m sotawhat.cli feedback listen" -WorkingDirectory $repo
    $logon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $listenSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName "sotawhat-feedback" -Action $listen -Trigger $logon -Settings $listenSettings `
        -Description "sotawhat 3.0 - votos do Telegram em tempo real" -Force | Out-Null
    Get-ScheduledTask -TaskName "sotawhat-feedback" | Select-Object TaskName, State
}

if ($Web) {
    # The graph interface (P3) at http://127.0.0.1:8765, up after every logon; it reads data\insight.db.
    # pythonw.exe has no console window; output goes to data\logs. Restarts if it crashes.
    $pythonw = Join-Path $repo ".venv\Scripts\pythonw.exe"
    if (-not (Test-Path $pythonw)) { throw "Not found: $pythonw" }
    $serve = New-ScheduledTaskAction -Execute $pythonw -Argument "-m sotawhat.cli serve --no-browser" -WorkingDirectory $repo
    $logonWeb = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $webSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    Register-ScheduledTask -TaskName "sotawhat-web" -Action $serve -Trigger $logonWeb -Settings $webSettings `
        -Description "sotawhat 3.0 - interface do grafo em http://127.0.0.1:8765" -Force | Out-Null
    Get-ScheduledTask -TaskName "sotawhat-web" | Select-Object TaskName, State
}

if ($Weekly) {
    # Trends, map, gaps, meta-review and the idea engine (P4), Sundays at 20:00: report in data\weekly,
    # ideas on Telegram (4 buttons each) and an e-mail copy. Stops at SOTAWHAT_LLM_BUDGET_USD_RUN_WEEKLY.
    $weeklyAction = New-ScheduledTaskAction -Execute $exe -Argument "run weekly" -WorkingDirectory $repo
    $sunday = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $WeeklyTime
    $weeklySettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 2)
    Register-ScheduledTask -TaskName "sotawhat-weekly" -Action $weeklyAction -Trigger $sunday -Settings $weeklySettings `
        -Description "sotawhat 3.0 - relatorio semanal e ideias (domingo)" -Force | Out-Null
    Get-ScheduledTask -TaskName "sotawhat-weekly" | Select-Object TaskName, State
}
