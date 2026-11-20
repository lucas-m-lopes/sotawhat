# scripts/vps_sync.ps1 — envia uma cópia consistente do insight.db para a VPS e reinicia a interface de lá.
#
#   .\scripts\vps_sync.ps1 -Vps usuario@minha-vps                 # cópia + envio + reinício
#   .\scripts\vps_sync.ps1 -Vps usuario@minha-vps -Dir sotawhat   # pasta do projeto na VPS (padrão: sotawhat)
#   .\scripts\vps_sync.ps1 -Vps usuario@minha-vps -SoCopia        # só gera a cópia local, não envia
#
# O que vai: o banco inteiro (itens, grafo, ideias, glossário e o índice do RAG com os vetores), cerca de
# 50 MB hoje. O que não vai: o .env, as chaves e a pasta config/. A cópia é feita pelo `sotawhat backup`
# (API de backup do SQLite), então pode rodar com o run diário em andamento. Na VPS o arquivo chega como
# insight.db.new e só troca de nome depois de inteiro; os votos dados na cópia antiga da VPS se perdem.
# Usa o ssh e o scp do Windows (OpenSSH) com a sua chave; nada de senha passa por este script.
param(
    [Parameter(Mandatory = $true)][string]$Vps,
    [string]$Dir = "sotawhat",
    [switch]$SoCopia
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $repo ".venv\Scripts\sotawhat.exe"
if (-not (Test-Path $exe)) { throw "não achei $exe: rode o script a partir do repositório com o .venv criado" }

Push-Location $repo
try {
    & $exe rag index | Out-Host                      # o índice do RAG viaja dentro do banco: deixe-o em dia
    & $exe backup | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "o backup falhou" }
    $dataDir = if ($env:SOTAWHAT_DATA_DIR) { $env:SOTAWHAT_DATA_DIR } else { Join-Path $repo "data" }
    $copy = Get-ChildItem (Join-Path $dataDir "backups") -Filter "insight-*.db" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $copy) { throw "nenhuma cópia em $dataDir\backups" }
    Write-Host "[cópia] $($copy.FullName) ($([math]::Round($copy.Length / 1MB, 1)) MB)"
    if ($SoCopia) { return }

    $remote = "$Dir/data"
    ssh $Vps "mkdir -p '$remote'"
    if ($LASTEXITCODE -ne 0) { throw "ssh falhou: confira o acesso a $Vps" }
    scp $copy.FullName "${Vps}:$remote/insight.db.new"
    if ($LASTEXITCODE -ne 0) { throw "scp falhou" }
    # troca atômica; os arquivos -wal/-shm da cópia antiga não valem para a nova
    ssh $Vps "cd '$Dir' && docker compose -f compose.vps.yaml stop sotawhat; mv -f data/insight.db.new data/insight.db && rm -f data/insight.db-wal data/insight.db-shm && docker compose -f compose.vps.yaml up -d"
    if ($LASTEXITCODE -ne 0) { throw "a troca do banco na VPS falhou (o arquivo enviado está em $remote/insight.db.new)" }
    Write-Host "[vps] banco atualizado e interface no ar: ssh -L 8765:127.0.0.1:8765 $Vps  ->  http://127.0.0.1:8765/#perguntar"
}
finally {
    Pop-Location
}
