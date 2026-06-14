# scripts/schedule_digest.ps1
param(
    [string]$Vault = "D:\Lucas\obsidian_vaults\ml_ai_med_vault",
    [string]$Python = "$PSScriptRoot\..\.venv\Scripts\sotawhat.exe",
    [int]$Limit = 10
)
& $Python digest --profile geral  --vault $Vault --limit $Limit
& $Python digest --profile medico --vault $Vault --limit $Limit
