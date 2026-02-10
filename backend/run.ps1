# Sobe a API (evita problema de uvicorn não estar no PATH no Windows)
# Uso: .\run.ps1   ou   .\run.ps1 -BindHost "0.0.0.0"   para acesso pela rede
# --workers 1: evita esgotar conexões do banco de autenticação (SAFS) "too many clients already"
param(
    [string]$BindHost = "127.0.0.1",
    [int]$Port = 8000
)
Set-Location $PSScriptRoot
python -m uvicorn app.main:app --reload --host $BindHost --port $Port --workers 1
