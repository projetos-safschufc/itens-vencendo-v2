# Analytics Inventário Hospitalar

Dashboard de analytics para inventário hospitalar: estoque a vencer (180 dias), histórico de itens vencidos, vencidos por ano e análise preditiva. Backend FastAPI + React (TypeScript), PostgreSQL (schema `gad_dlih_safs`), autenticação JWT e autorização por roles.

## Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic, JWT (python-jose), cache em memória (TTL)
- **Frontend:** React 18, TypeScript, Vite, Material UI, Recharts, React Query
- **Banco:** PostgreSQL (view `v_df_estoque`, view/tabela `v_df_movimento` / `df_movimento`)

## Regras de negócio

- Filtro por listas fixas de almoxarifados UACE e ULOG (configurável em `backend/app/constants.py`).
- Relacionamento material: `SPLIT_PART(v_df_estoque.nome_do_material, '-', 1) = SPLIT_PART(v_df_movimento.mat_cod_antigo, '-', 1)`.
- Estoque a vencer: `saldo > 0` e `validade` entre hoje e hoje + 180 dias.
- Perdas por validade: `movimento_subtipo = 'PERDAS POR VALIDADE'`.
- Análise preditiva: consumo médio últimos 6 meses (dados a partir de 2023); cache TTL 60s.

## Configuração

### Senha do banco com caracteres especiais (#, @, etc.)

A senha de acesso ao PostgreSQL (ex.: `abi123!@#qwe`) contém `#`, que em arquivos `.env` é interpretado como início de comentário. Para funcionar corretamente:

1. **No arquivo `.env`**: use **aspas duplas** em volta da senha:
   ```env
   DB_PASSWORD="abi123!@#qwe"
   ```
2. **Na aplicação**: a URL de conexão é montada com codificação URL (ex.: `#` → `%23`), então o acesso ao banco é efetivado mesmo com esses caracteres. Nada mais é necessário no código.

### Backend

```bash
cd backend
cp .env.example .env
# Edite .env com DB_HOST, DB_USER, DB_PASSWORD (com aspas se tiver #), DB_SCHEMA, JWT_SECRET_KEY
pip install -e .   # ou: uv pip install -e .
```

Variáveis principais no `.env`:

- `DB_*` (banco dw – analytics) e `AUTH_DB_*` (safs – ctrl.users). Senhas com `#`: use aspas.
- `JWT_SECRET_KEY` (obrigatório em produção)
- `CORS_ORIGINS` (inclua a URL do frontend na rede, ex.: `http://10.28.0.124:5173`)

**Login:** usuários vêm da tabela **ctrl.users** (banco SAFS, schema ctrl). Use e-mail e senha cadastrados. **Cadastro:** apenas admin, via menu "Cadastrar usuário" ou `POST /auth/register`. Mapeamento de perfil: profile_id 1 = admin, 2 = analyst, 3 = read_only (em `app/constants.py`). Para gerar hash de senha (ex.: script de migração):

```bash
python -m scripts.hash_password
# Cole o hash em app/dependencies.py em DEMO_USERS
```

Subir API (use `python -m uvicorn` no Windows se o comando `uvicorn` não for encontrado):

```bash
python -m uvicorn app.main:app --reload --port 8000
```

Documentação: **http://localhost:8000/docs**

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Acesse **http://localhost:5173**. A API é chamada em `/api` (proxy em desenvolvimento para `http://localhost:8000`). Em produção, configure `VITE_API_URL` para a URL do backend.

---

## Implantação em rede interna (ex.: 10.28.0.124)

**Mini tutorial (VM):** para executar em uma máquina virtual e outros usuários acessarem, veja **[docs/TUTORIAL_VM.md](docs/TUTORIAL_VM.md)**.

**Docker não é obrigatório.** Em rede interna você pode rodar backend e frontend diretamente no servidor (Windows ou Linux).

### Sem Docker (recomendado para rede interna)

1. **No servidor (ex.: 10.28.0.124)**  
   - Instale Python 3.11+, Node 18+ e configure o `.env` do backend (com `DB_PASSWORD` entre aspas se tiver `#`).

2. **Backend** – escute em todas as interfaces para acesso pela rede:
   ```bash
   cd backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   - A API ficará em `http://10.28.0.124:8000`.

3. **CORS** – no `.env` do backend, inclua a origem do frontend:
   ```env
   CORS_ORIGINS=["http://localhost:5173","http://10.28.0.124:5173","http://10.28.0.124:3000"]
   ```

4. **Frontend** – em modo desenvolvimento:
   ```bash
   cd frontend
   npm run dev
   ```
   Acesse de outros PCs por `http://10.28.0.124:5173`.  
   Ou gere o build e sirva com um servidor estático:
   ```bash
   npm run build
   npx serve -s dist -l 3000
   ```
   Acesse `http://10.28.0.124:3000` e configure `VITE_API_URL=http://10.28.0.124:8000` antes do build (ou use proxy no servidor).

5. **Firewall**: libere as portas 8000 (API) e 5173/3000 (frontend) no servidor, se necessário.

### Com Docker (opcional)

Na raiz do projeto (com `.env` no `backend/` com `DB_PASSWORD` entre aspas e `JWT_SECRET_KEY`):

```bash
docker compose up -d
```

- API: http://localhost:8000 (ou http://10.28.0.124:8000 pela rede)  
- Frontend: http://localhost:5173 (ou http://10.28.0.124:5173 pela rede)

Para acesso pela rede, use no `.env`: `CORS_ORIGINS=["http://10.28.0.124:5173","http://localhost:5173"]`.

## Rotas frontend

| Rota               | Descrição                    |
|--------------------|------------------------------|
| `/login`          | Login (JWT)                   |
| `/dashboard`      | Estoque a vencer 180 dias     |
| `/expired-items`  | Histórico itens vencidos      |
| `/expired-yearly` | Vencidos por ano (YoY)        |
| `/predictive`     | Análise preditiva             |

## Endpoints API (resumo)

- **Auth:** `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- **Dashboard:** `GET /dashboard/stock-expiry`, `GET /dashboard/metrics`, `GET /dashboard/charts`, `POST /dashboard/export/pdf`
- **Expired items:** `GET /expired-items`, `GET /expired-items/metrics`, `GET /expired-items/charts`, `POST /expired-items/export/csv`
- **Expired yearly:** `GET /expired-yearly`
- **Predictive:** `POST /predictive/query`, `POST /predictive/export/excel`, `POST /predictive/export/csv`

Todos os endpoints de dados (exceto auth) exigem `Authorization: Bearer <access_token>` e role compatível (admin, analyst, read_only).

## Ajuste ao seu schema

Os repositórios em `backend/app/repositories/` assumem colunas como:

- **Estoque (`v_df_estoque`):** `nome_do_material`, `validade`, `saldo`, `valor_unitario`, `almoxarifado`, `grupo`
- **Movimento (`v_df_movimento`/`df_movimento`):** `mat_cod_antigo`, `movimento_subtipo`, `data_movimento`, `quantidade`, `valor_unitario`, `almoxarifado`, `grupo`

Se os nomes no seu banco forem diferentes, altere os SQLs nos repositórios e as listas UACE/ULOG em `constants.py`.
