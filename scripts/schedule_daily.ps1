# scripts/schedule_daily.ps1 - registers `sotawhat run daily` in Windows Task Scheduler (SDD 6.12, 8.3).
# Usage, from the repository root in PowerShell:
#   .\scripts\schedule_daily.ps1                         # 07:00, again at 10:00 and 14:00 if it did not finish ok
#   .\scripts\schedule_daily.ps1 -Listener               # also: Telegram feedback listener at logon (P1)
#   .\scripts\schedule_daily.ps1 -Web                    # also: graph interface at logon (P3)
#   .\scripts\schedule_daily.ps1 -Weekly                 # also: weekly report and ideas, Sundays 20:00 (P4)
#   .\scripts\schedule_daily.ps1 -RetryAt @()            # no second chances, only 07:00 and the logon
# Runs as the current user while logged on; a missed run starts as soon as possible (StartWhenAvailable).
# A restart while logged off (Windows Update, 03:15 on 2026-11-11) still skipped the 07:00 run, so the task also
# fires at logon with `--catch-up <Time>`: it runs only after <Time> and while today's daily has not finished ok.
# 2026-11-21: the 07:00 run met the PC busy with another project's 3D simulations. At the Task Scheduler's default
# priority (7, below normal) its start took 29 min instead of 2 s, the 1 h limit killed it at 08:00 before it had
# collected anything, and nothing tried again (nobody logged on). Since then: normal priority, a 3 h limit (weekly:
# 4 h), and the same `--catch-up` at each -RetryAt time, a 2-second no-op once today's daily has finished ok.
param(
    [string]$Time = "07:00",
    [string[]]$RetryAt = @("10:00", "14:00"),
    [string]$TaskName = "sotawhat-daily",
    [switch]$Listener,
    [switch]$Web,
    [switch]$Weekly,
    [string]$WeeklyTime = "20:00"
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path "$PSScriptRoot\..").Path
# pythonw.exe has no console window: a run used to die when its black window was closed (exit 0xC000013A,
# the first weekly run on 2026-11-08). Logs stay in data\logs; prints and tracebacks go to data\logs\console.log.
$exe = Join-Path $repo ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $exe)) { throw "Not found: $exe - install first: uv pip install -e .[dev]" }
if (-not (Test-Path (Join-Path $repo ".env"))) { Write-Warning "No .env in $repo - copy .env.example to .env and fill it in." }

$arguments = "-m sotawhat.cli run daily --catch-up $Time"
# Normal priority (0 = highest, 10 = lowest): the runs share the CPU fairly with whatever else is busy. The daily
# is mostly network waits, so it takes little from the rest.
$priority = 5

# WorkingDirectory = repo root, so the `.env` file, `config\` and `data\insight.db` are found.
$action = New-ScheduledTaskAction -Execute $exe -Argument $arguments -WorkingDirectory $repo
$trigger = New-ScheduledTaskTrigger -Daily -At $Time
$atLogon = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$atLogon.Delay = "PT2M"   # let the network come up first; an ordinary logon only logs "[catch-up] ... já rodou"
# Second chances: a daily that failed or was killed runs again the same day. While one is still running the task
# ignores the trigger (IgnoreNew), so a run killed at the 3 h limit right at 10:00 waits for 14:00.
$retries = @($RetryAt | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ })
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3) -Priority $priority
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger (@($trigger, $atLogon) + $retries) `
    -Settings $settings -Description "sotawhat 3.0 - coleta diaria + resumo no Telegram" -Force | Out-Null
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
    $weeklyAction = New-ScheduledTaskAction -Execute $exe -Argument "-m sotawhat.cli run weekly" -WorkingDirectory $repo
    $sunday = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $WeeklyTime
    $weeklySettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Hours 4) -Priority $priority
    Register-ScheduledTask -TaskName "sotawhat-weekly" -Action $weeklyAction -Trigger $sunday -Settings $weeklySettings `
        -Description "sotawhat 3.0 - relatorio semanal e ideias (domingo)" -Force | Out-Null
    Get-ScheduledTask -TaskName "sotawhat-weekly" | Select-Object TaskName, State
}
