# Mini tutorial: executar em uma VM para outros usuários acessarem

Este guia mostra como rodar o **Analytics Inventário** em uma **máquina virtual (VM)** para que outros usuários na rede acessem pelo navegador.

**Substitua `IP_DA_VM`** pelo IP real da sua VM (ex.: `10.28.0.124`). Para descobrir o IP no Windows: `ipconfig` → procure "Endereço IPv4".

---

## Requisitos na VM

- **Windows** (ou Linux; comandos equivalentes no README).
- **Python 3.11+** e **Node.js 18+** (npm).
- Acesso de rede ao **PostgreSQL** (ex.: 10.28.0.159) e ao banco **SAFS** (auth).

---

## Passo 1 – Copiar o projeto para a VM

Copie a pasta do projeto (ex.: `app_validade`) para a VM (ex.: `C:\app_validade`).  
Ou clone do Git:

```powershell
git clone <URL_DO_REPOSITORIO> C:\app_validade
cd C:\app_validade
```

---

## Passo 2 – Configurar o backend na VM

1. Abra um terminal na pasta do projeto e entre no backend:
   ```powershell
   cd C:\app_validade\backend
   ```

2. Crie o `.env` a partir do exemplo:
   ```powershell
   Copy-Item .env.example .env
   ```

3. Edite o `.env` e confira:
   - **Banco de dados:** `DB_HOST`, `DB_USER`, `DB_NAME`, `DB_PASSWORD` (e `AUTH_DB_*` para login).
   - **CORS:** inclua o endereço em que o frontend será acessado (troque pelo IP da sua VM):
     ```env
     CORS_ORIGINS=["http://localhost:5173","http://IP_DA_VM:5173","http://IP_DA_VM","http://IP_DA_VM:80"]
     ```

4. Crie o ambiente virtual e instale dependências:
   ```powershell
   cd C:\app_validade
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   cd backend
   pip install -r requirements.txt
   pip install -e .
   ```

---

## Passo 3 – Configurar o frontend na VM

1. Em outro terminal (ou depois de subir o backend), entre no frontend:
   ```powershell
   cd C:\app_validade\frontend
   ```

2. Crie o `.env` e aponte a API para o IP da VM:
   ```powershell
   Copy-Item .env.example .env
   ```
   No `.env`, deixe (troque `IP_DA_VM` pelo IP real da VM):
   ```env
   VITE_API_URL=http://IP_DA_VM:8000
   ```

3. Instale dependências:
   ```powershell
   npm install
   ```

---

## Passo 4 – Subir backend e frontend na VM

**Terminal 1 – Backend** (aceitando conexões da rede):

```powershell
cd C:\app_validade
.\.venv\Scripts\Activate.ps1
cd backend
.\run-server.ps1
```

A API ficará em **http://IP_DA_VM:8000**.

**Terminal 2 – Frontend**:

```powershell
cd C:\app_validade\frontend
npm run dev
```

O frontend ficará em **http://IP_DA_VM:5173** (o Vite escuta em todas as interfaces por padrão).

---

## Passo 5 – Liberar portas no firewall da VM (Windows)

Para outros PCs acessarem, permita as portas **8000** e **5173**.  
No PowerShell **como Administrador**:

```powershell
New-NetFirewallRule -DisplayName "Analytics API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
New-NetFirewallRule -DisplayName "Analytics Frontend" -Direction Inbound -Protocol TCP -LocalPort 5173 -Action Allow
```

---

## Como os outros usuários acessam

| O que              | URL                          |
|--------------------|------------------------------|
| **Aplicação**      | http://IP_DA_VM:5173         |
| Documentação da API| http://IP_DA_VM:8000/docs    |

Os usuários abrem **http://IP_DA_VM:5173** no navegador e fazem login com usuário do **ctrl.users (SAFS)**.

---

## Resumo rápido

1. Copiar/clonar o projeto na VM.  
2. Backend: `.env` com banco e **CORS** com `http://IP_DA_VM:5173` (e outras URLs usadas).  
3. Frontend: `.env` com `VITE_API_URL=http://IP_DA_VM:8000`.  
4. Subir backend (`.\run-server.ps1`) e frontend (`npm run dev`).  
5. Firewall: permitir TCP 8000 e 5173.  
6. Outros usuários acessam **http://IP_DA_VM:5173**.

Para **produção** (build estático + IIS/nginx), veja **DEPLOY_SERVIDOR.md**.
