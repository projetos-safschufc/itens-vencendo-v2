# Sobe a API no servidor para acesso por outros usuários na rede.
# Bind em 0.0.0.0 para aceitar conexões de qualquer interface (ex.: IP 10.28.0.124).
# Uso no servidor Windows: .\run-server.ps1
# Outros usuários acessam: http://10.28.0.124:5173 (frontend) e a API em :8000.
param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000
)
Set-Location $PSScriptRoot
python -m uvicorn app.main:app --reload --host $BindHost --port $Port --workers 1
