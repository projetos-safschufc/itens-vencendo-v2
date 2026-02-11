# Publicar no servidor Windows (10.28.0.124) e permitir acesso de outros usuários

Este guia descreve como publicar o **Analytics Inventário** no servidor Windows com IP **10.28.0.124** para que outros usuários na rede acessem pelo navegador.

---

## Visão geral

- **Servidor:** Windows com IP 10.28.0.124.
- **Backend (API):** roda no servidor escutando em **0.0.0.0:8000** (aceita conexões de qualquer interface).
- **Frontend:** roda no servidor (Vite dev na porta 5173 ou build estático servido por IIS/nginx).
- **Outros usuários:** acessam no navegador **http://10.28.0.124:5173** (ou a URL onde o frontend estiver exposto).

Requisitos no servidor: Python 3.11+, Node.js 18+, rede até o host PostgreSQL (ex.: 10.28.0.159, configurado no .env).

---

## 1. Backend no servidor

### 1.1. Copiar projeto e configurar ambiente

No servidor (10.28.0.124), na pasta do projeto (ex.: `C:\app_validade\backend`):

1. Copie o `.env.example` para `.env` e preencha (incluindo senhas em `.env.password` se usar).
2. Confirme que **CORS_ORIGINS** no `.env` inclui as origens do frontend no servidor, por exemplo:
   ```env
   CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://10.28.0.124:5173","http://10.28.0.124:3000","http://10.28.0.124","http://10.28.0.124:80"]
   ```

### 1.2. Subir a API aceitando conexões da rede

Na pasta `backend`, use o script que já faz bind em **0.0.0.0**:

```powershell
.\run-server.ps1
```

Ou manualmente:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --workers 1
```

A API ficará acessível em:

- **No próprio servidor:** http://localhost:8000 e http://10.28.0.124:8000  
- **De outros PCs:** http://10.28.0.124:8000  
- **Documentação:** http://10.28.0.124:8000/docs  

---

## 2. Frontend no servidor (para outros usuários acessarem)

### Opção A – Modo desenvolvimento (Vite dev server)

1. Na pasta `frontend`, crie o `.env` a partir do exemplo:
   ```powershell
   Copy-Item .env.example .env
   ```
2. No `.env`, deixe a API apontando para o IP do servidor (já vem no exemplo):
   ```env
   VITE_API_URL=http://10.28.0.124:8000
   ```
3. Instale dependências e suba o frontend:
   ```powershell
   npm install
   npm run dev
   ```
   O Vite sobe na porta 5173 e, por padrão, escuta em todas as interfaces.

Outros usuários acessam no navegador: **http://10.28.0.124:5173**

### Opção B – Build de produção e servir com IIS ou outro servidor web

1. No `frontend`, crie `.env` com a URL da API do servidor:
   ```env
   VITE_API_URL=http://10.28.0.124:8000
   ```
2. Gere o build:
   ```powershell
   npm install
   npm run build
   ```
3. A pasta `dist` conterá os arquivos estáticos. Publique essa pasta no IIS (ou nginx/Apache) no servidor, por exemplo em:
   - **http://10.28.0.124** (porta 80) ou  
   - **http://10.28.0.124:3000**  

4. No `.env` do **backend**, o `CORS_ORIGINS` deve incluir a URL em que o frontend é servido (ex.: `http://10.28.0.124` e `http://10.28.0.124:80` se for na porta 80).

---

## 3. Firewall do Windows (servidor)

Para outros PCs acessarem as portas do servidor:

1. Abra **Firewall do Windows com Segurança Avançada**.
2. Crie regras de **entrada** permitindo TCP:
   - **Porta 8000** (API)
   - **Porta 5173** (se usar Vite dev) ou a porta em que o frontend estiver (ex.: 80).

Ou via PowerShell (execute como Administrador):

```powershell
New-NetFirewallRule -DisplayName "Analytics API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
New-NetFirewallRule -DisplayName "Analytics Frontend" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
```

---

## 4. Resumo para acesso de outros usuários

| O que                | URL (outros usuários)        |
|----------------------|-----------------------------|
| Aplicação (frontend) | http://10.28.0.124:5173      |
| API (backend)        | http://10.28.0.124:8000      |
| Documentação da API  | http://10.28.0.124:8000/docs |

1. No servidor: subir o backend com `.\run-server.ps1` (ou comando equivalente com `--host 0.0.0.0`).
2. No servidor: subir o frontend com `npm run dev` (ou publicar o `dist` no IIS).
3. Nos outros PCs: abrir **http://10.28.0.124:5173** no navegador e fazer login com usuário do ctrl.users (SAFS).

---

## 5. Problemas comuns

| Problema | Solução |
|----------|--------|
| CORS ao acessar de outro PC | Incluir em `CORS_ORIGINS` a URL usada no navegador (ex.: `http://10.28.0.124:5173`). |
| Não conecta à API | Backend deve estar com `--host 0.0.0.0`; verificar firewall (porta 8000). |
| Frontend não carrega | Verificar firewall (porta 5173 ou 80); confirmar `VITE_API_URL=http://10.28.0.124:8000` no `.env` do frontend antes do build. |
| "Too many clients" (SAFS) | Reduzir pool do auth em `app/db/session.py` e/ou usar `--workers 1`; ver avaliação de conexões no projeto. |
