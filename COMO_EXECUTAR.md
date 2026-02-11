# Como executar a aplicação – Passo a passo

**Requisitos:** Python 3.11+, Node.js 18+ (com npm), acesso à rede do PostgreSQL (host no .env, ex.: 10.28.0.159).

**Pasta do projeto:** navegue até a raiz do projeto (ex.: `c:\...\app_validade`) antes de seguir os passos.

---

## 1. Backend (API)

### 1.1. Entrar na pasta do backend

```powershell
cd backend
```

(Se estiver na raiz do projeto: `cd app_validade\backend` no Windows ou `cd app_validade/backend` no Linux/Mac.)

### 1.2. Criar o arquivo `.env`

Copie o exemplo e **mantenha a senha entre aspas** (obrigatório quando há `#`):

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Windows (CMD) ou Linux/Mac:**
```bash
cp .env.example .env
```

Abra o `.env` e confira:

- `DB_HOST`, `DB_USER`, `DB_NAME`, `DB_SCHEMA` (o exemplo já vem preenchido).
- `DB_PASSWORD="abi123!@#qwe"` — **não remova as aspas**.
- **Auth (ctrl.users):** `AUTH_DB_*` apontam para o banco **SAFS** (porta 5433). Use aspas em `AUTH_DB_PASSWORD` se a senha tiver `#`.
- Para acesso pela rede (ex.: 10.28.0.124), inclua em `CORS_ORIGINS` as URLs do frontend (o exemplo já pode conter).

### 1.3. Instalar dependências do Python

**Se você usa ambiente virtual (.venv):** ative-o antes de instalar, senão o `uvicorn` e o `app` não serão encontrados ao rodar a API.

- **Ativar no Windows (PowerShell):** na raiz do projeto (ex.: `app_validade`), execute `.\.venv\Scripts\Activate.ps1`. O prompt deve passar a mostrar `(.venv)`.
- Em seguida, entre na pasta `backend` e rode os comandos abaixo (o prompt deve mostrar `(.venv)`).

**Opção A – requirements.txt (recomendado):**
```powershell
pip install -r requirements.txt
pip install -e .
```

**Opção B – só o projeto:**
```powershell
pip install -e .
```

**Opção C – uv (se tiver instalado):**
```powershell
uv pip install -e .
```

### 1.4. Subir a API

Use **`python -m uvicorn`** para não depender do `uvicorn` estar no PATH (recomendado no Windows):

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

**Alternativa no Windows (PowerShell):** na pasta `backend`:

- Só local: `.\run.ps1`
- Acesso pela rede: `.\run.ps1 -BindHost "0.0.0.0"`
- Outra porta: `.\run.ps1 -Port 8001`

Equivalente em linha de comando para rede:

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**No servidor Windows (para outros usuários acessarem):** use o script que já faz bind em todas as interfaces:

```powershell
.\run-server.ps1
```

Consulte **DEPLOY_SERVIDOR.md** na raiz do projeto para publicar no servidor (ex.: 10.28.0.124) e permitir acesso de outros usuários.

Deixe este terminal aberto. A API ficará em:

- **http://localhost:8000**
- Documentação: **http://localhost:8000/docs**

---

## 2. Frontend

Abra **outro terminal** (a API continua rodando no primeiro).

### 2.1. Entrar na pasta do frontend

```powershell
cd frontend
```

(Se estiver na raiz: `cd app_validade\frontend` no Windows. Se estiver em `backend`: `cd ..\frontend`.)

### 2.2. Instalar dependências

```powershell
npm install
```

### 2.3. Subir o frontend

```powershell
npm run dev
```

O navegador pode abrir sozinho. Se não abrir, acesse **http://localhost:5173**.

O frontend usa proxy para a API em `http://localhost:8000`; em desenvolvimento não é preciso configurar URL da API.

---

## 3. Acessar a aplicação

1. Abra **http://localhost:5173** no navegador.
2. Na tela de login use **e-mail** e **senha** de um usuário cadastrado na tabela **ctrl.users** (banco SAFS). Perfis: profile_id 1 = admin, 2 = analista, 3 = somente leitura.
3. Após o login: Dashboard, Itens vencidos, Vencidos por ano, Análise preditiva. **Admin** vê também o menu "Cadastrar usuário".

---

## 4. Resumo rápido (com .env já criado)

**Terminal 1 – Backend:**
```powershell
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Ou no Windows: `cd backend` e depois `.\run.ps1`.

**Terminal 2 – Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

Acesse **http://localhost:5173** e faça login com o e-mail e senha de um usuário em ctrl.users.

---

## 5. Problemas comuns

| Problema | O que fazer |
|----------|-------------|
| Erro de conexão com o banco | Verifique rede/VPN até o host do `.env` (ex.: 10.28.0.159) e se `DB_PASSWORD` está **entre aspas** no `.env`. |
| CORS ao acessar por outro PC | No `.env` do backend, inclua a URL do frontend em `CORS_ORIGINS` (ex.: `"http://10.28.0.124:5173"`) e suba a API com `--host 0.0.0.0` ou `.\run.ps1 -BindHost "0.0.0.0"`. |
| Porta 8000 ou 5173 em uso | Backend em outra porta: `python -m uvicorn app.main:app --reload --port 8001` (ou `.\run.ps1 -Port 8001`). No frontend, ajuste o proxy em `vite.config.ts` (target para `http://localhost:8001`). |
| Login não aceita admin123 | Na pasta `backend`: `python scripts/hash_password.py`. Cole o hash gerado em `app/dependencies.py`, no campo `hashed_password` do usuário desejado. |
| "uvicorn" não reconhecido | Use sempre `python -m uvicorn ...` ou, no Windows, `.\run.ps1`. |
| "No module named uvicorn" | O `.venv` não tem as dependências. **Solução garantida:** use o pip do próprio .venv (na raiz do projeto, ex.: `app_validade`): `.\.venv\Scripts\pip.exe install -r backend\requirements.txt` e depois `.\.venv\Scripts\pip.exe install -e backend`. Em seguida, com o .venv ativado, na pasta `backend`: `python -m uvicorn app.main:app --reload --port 8000`. |

---

## 6. Parar a aplicação

Em cada terminal onde a API ou o frontend está rodando, pressione **Ctrl+C**.
