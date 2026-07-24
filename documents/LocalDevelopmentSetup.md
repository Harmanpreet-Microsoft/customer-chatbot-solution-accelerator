# Local Development Setup Guide

This guide walks you through running the Customer Chatbot Solution Accelerator on your local machine for development.

## Important Setup Notes

### Multi-App Architecture

The accelerator ships as **two independent apps**, each with its own backend and frontend:

| App | Backend | Frontend | Purpose |
|-----|---------|----------|---------|
| `chat-app/` | FastAPI (`chat-app/backend/`) | React + Vite (`chat-app/frontend/`) | Standalone chat host + embeddable chat widget |
| `scenario-app/` | FastAPI (`scenario-app/backend/`) | React + Vite (`scenario-app/frontend/`) | Scenario host UI (ecommerce / healthcare / banking) that embeds the chat widget |

You do **not** need to run all four services at once. Typical local workflows:

- **Chat only** — run `chat-app/backend` + `chat-app/frontend`
- **Scenario + Chat** — run all four (the scenario frontend calls both its own backend and the chat backend)

> **⚠️ Each service needs its own terminal**
>
> - Do **not** close terminals while services are running
> - Open one terminal per service
> - Each terminal will stream live logs

### Path Conventions

All paths in this guide are relative to the repository root:

```
customer-chatbot-solution-accelerator/       ← Repository root (start here)
├── chat-app/
│   ├── backend/                             ← FastAPI chat backend
│   │   ├── app/                             ← Application code
│   │   ├── env.sample                       ← Env template (copy to .env)
│   │   ├── requirements.txt                 ← Python dependencies
│   │   └── startup.sh                       ← Container startup script
│   └── frontend/                            ← React + Vite chat frontend
│       ├── src/
│       ├── package.json
│       └── vite.config.ts                   ← Dev server on port 3001
├── scenario-app/
│   ├── backend/                             ← FastAPI scenario host backend
│   │   ├── app/
│   │   ├── env.sample
│   │   └── requirements.txt
│   └── frontend/                            ← React + Vite scenario host UI
│       ├── src/
│       ├── package.json
│       └── vite.config.ts                   ← Dev server on port 5173
├── scenarios/                               ← Scenario packs (ecommerce/healthcare/banking)
│   ├── ecommerce/
│   ├── healthcare/
│   └── banking/
├── infra/                                   ← Bicep infrastructure
│   ├── main.bicep
│   ├── main.parameters.json
│   ├── main.waf.parameters.json
│   ├── bicep/                               ← Vanilla Bicep modules (dev/test)
│   ├── avm/                                 ← Azure Verified Modules (production/WAF)
│   └── scripts/                             ← Pre/post-provision scripts
├── documents/                               ← Documentation (you are here)
├── .vscode/
└── azure.yaml                               ← Azure Developer CLI config
```

**Verify you are at the repo root before running any command:**

```bash
# Linux/macOS
pwd    # should end in .../customer-chatbot-solution-accelerator

# Windows PowerShell
Get-Location    # should end in ...\customer-chatbot-solution-accelerator

# If not, navigate there
cd path/to/customer-chatbot-solution-accelerator
```

---

## Step 1: Prerequisites — Install Required Tools

- [Visual Studio Code](https://code.visualstudio.com/) with these extensions:
  - [Azure Tools](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-node-azure-pack)
  - [Bicep](https://marketplace.visualstudio.com/items?itemName=ms-azuretools.vscode-bicep)
  - [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
  - [Pylance](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance)
- [Python 3.11+](https://www.python.org/downloads/) — check "Add Python to PATH" during installation
- [PowerShell 7.0+](https://github.com/PowerShell/PowerShell#get-powershell) (Windows)
- [Node.js LTS](https://nodejs.org/en) — required for both frontends
- [Git](https://git-scm.com/downloads)
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
- [Bicep CLI 0.33.0+](https://learn.microsoft.com/azure/azure-resource-manager/bicep/install)

### Windows (PowerShell)

```powershell
winget install Python.Python.3.11
winget install Git.Git
winget install OpenJS.NodeJS.LTS
winget install Microsoft.AzureCLI
winget install Microsoft.Azd
```

### Ubuntu/Debian

```bash
sudo apt update && sudo apt install python3.11 python3.11-venv git curl nodejs npm -y
```

### RHEL/CentOS/Fedora

```bash
sudo dnf install python3.11 python3.11-devel git curl gcc nodejs npm -y
```

---

## Step 2: Clone the Repository

```bash
git clone https://github.com/microsoft/customer-chatbot-solution-accelerator.git
cd customer-chatbot-solution-accelerator
code .
```

---

## Step 3: Azure Authentication

Local development uses `DefaultAzureCredential` against the Azure resources you have provisioned.

```bash
az login
az account set --subscription "<your-subscription-id>"
az account show
```

---

## Step 4: Deploy Azure Resources

The backends talk to real Azure services (Azure AI Foundry, Azure OpenAI, Azure AI Serach, Azure Cosmos DB). Provision them first:

```bash
azd auth login
azd up
```

📖 See the [Deployment Guide](./DeploymentGuide.md) for the full deployment flow (including scenario selection and post-provision data/agent scripts).

After `azd up` completes, run the post-provision data upload and agent creation scripts described in the Deployment Guide — the backends need the Azure AI Foundry agent names in order to serve requests.

---

## Step 5: Configure Environment Variables

Each backend loads settings from a `.env` file in its own directory. Copy the sample and fill in values from your `azd` environment (`.azure/<env-name>/.env` after `azd up`).

### 5.1 Chat backend — `chat-app/backend/.env`

```bash
# From repo root (bash / macOS / Linux / WSL)
cp chat-app/backend/env.sample chat-app/backend/.env
```

```powershell
# From repo root (Windows PowerShell)
Copy-Item chat-app/backend/env.sample chat-app/backend/.env
```

Populate the file with the endpoints/keys from your provisioned resources. Minimum values for local dev:

```env
# App
APP_ENV=dev
ALLOWED_ORIGINS_STR=http://localhost:3001,http://localhost:5173

# Azure AI Foundry / Azure OpenAI
AZURE_AI_AGENT_ENDPOINT=https://<your-ai-services>.services.ai.azure.com/api/projects/<project>
AZURE_OPENAI_ENDPOINT=https://<your-openai>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-01-01-preview

# Azure Azure AI Serach
AZURE_AI_SEARCH_ENDPOINT=https://<your-search>.search.windows.net

# Azure Cosmos DB
COSMOS_DB_ENDPOINT=https://<your-cosmos>.documents.azure.com:443/

# Foundry agent names (created by the post-provision agent script)
FOUNDRY_CHAT_AGENT=<chat-agent-name>
FOUNDRY_PRODUCT_AGENT=<product-agent-name>
FOUNDRY_POLICY_AGENT=<policy-agent-name>
```

> **⚠️ Set `APP_ENV=dev`.** If you copied values from `.azure/<env-name>/.env`, `APP_ENV` will be set for the deployed environment. You **must** change it to `dev` locally — this switches the backend to `DefaultAzureCredential` so it uses your `az login` identity instead of the App Service managed identity.

> `FOUNDRY_*` values are **not** populated automatically by `azd up`. Run the post-provision agent creation script (see Deployment Guide § 5.3) and copy the resulting names into `.env`.

### 5.2 Scenario backend — `scenario-app/backend/.env`

```bash
# bash / macOS / Linux / WSL
cp scenario-app/backend/env.sample scenario-app/backend/.env
```

```powershell
# Windows PowerShell
Copy-Item scenario-app/backend/env.sample scenario-app/backend/.env
```

The scenario backend needs Cosmos + Azure OpenAI (and Application Insights, optionally). Fill in the same Azure endpoints as above.

> **Port note:** Both backends default to port `8000`. For local dev, run the chat backend on `8001` (matches its Dockerfile) so the two do not collide. See Step 6.

### 5.3 Frontends

The frontends read `VITE_API_BASE_URL` at build time (Vite `.env`) or at runtime via a generated `runtime-config.js` in production. For local dev, create a `.env` file next to each `package.json`:

**`chat-app/frontend/.env`**

```env
VITE_API_BASE_URL=http://localhost:8001
```

**`scenario-app/frontend/.env`**

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_CHAT_API_BASE_URL=http://localhost:8001
VITE_SCENARIO=ecommerce
```

> If `VITE_API_BASE_URL` is not set, the frontend defaults to `http://localhost:8000` (see [chat-app/frontend/src/lib/api.ts](../chat-app/frontend/src/lib/api.ts) and [scenario-app/frontend/src/lib/api.ts](../scenario-app/frontend/src/lib/api.ts)).

### 5.4 Required Azure RBAC (once per user)

If the post-provision hook already assigned roles, skip this. Otherwise grant your user identity:

```bash
PRINCIPAL_ID=$(az ad signed-in-user show --query id -o tsv)

# Azure Cosmos DB data plane access
az cosmosdb sql role assignment create \
  --account-name <cosmos-account> \
  --resource-group <resource-group> \
  --role-definition-name "Azure Cosmos DB Built-in Data Contributor" \
  --principal-id "$PRINCIPAL_ID" \
  --scope "/"

# Azure AI Serach data plane access
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Search Index Data Contributor" \
  --scope "/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.Search/searchServices/<search-name>"
```

---

## Step 6: Run the Applications

### 6.1 Create Python virtual environments

Each backend has its own `requirements.txt`. Use one venv per backend (or a shared venv at the repo root — both approaches work; the examples below use a shared root venv).

```bash
# From repo root
python -m venv .venv

# Activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows CMD
.venv\Scripts\activate.bat
# macOS/Linux
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

### 6.2 Install backend dependencies

```bash
# Chat backend
pip install --upgrade pip
pip install -r chat-app/backend/requirements.txt

# Scenario backend (only if you plan to run it)
pip install -r scenario-app/backend/requirements.txt
```

### 6.3 Install frontend dependencies

```bash
# Chat frontend
cd chat-app/frontend && npm install && cd -

# Scenario frontend
cd scenario-app/frontend && npm install && cd -
```

### 6.4 Start each service in its own terminal

Recommended port layout for running everything locally:

| Service | Directory | Port |
|---------|-----------|------|
| Chat backend | `chat-app/backend` | **8001** |
| Chat frontend | `chat-app/frontend` | **3001** (Vite default for this app) |
| Scenario backend | `scenario-app/backend` | **8000** |
| Scenario frontend | `scenario-app/frontend` | **5173** (Vite default) |

**Terminal 1 — Chat backend (port 8001):**

```bash
cd chat-app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 2 — Chat frontend (port 3001):**

```bash
cd chat-app/frontend
npm run dev
```

**Terminal 3 — Scenario backend (port 8000):** *(only if running scenario host)*

```bash
cd scenario-app/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 4 — Scenario frontend (port 5173):** *(only if running scenario host)*

```bash
cd scenario-app/frontend
npm run dev
```

### 6.5 VS Code Debug

Ready-to-use debug configurations are provided in [`.vscode/launch.json`](../.vscode/launch.json):

- **Chat backend (uvicorn, reload)** — runs `chat-app/backend` on port `8001` with `chat-app/backend/.env`
- **Scenario backend (uvicorn, reload)** — runs `scenario-app/backend` on port `8000` with `scenario-app/backend/.env`
- **Chat + Scenario backends** (compound) — launches both backends together with a single F5

Open **Run and Debug** (`Ctrl+Shift+D`), pick the configuration, and press F5. The frontends are still started from the terminal (`npm run dev` in each frontend directory).

> The configurations assume a shared virtual environment at `${workspaceFolder}/.venv` (created in § 6.1). If you use a per-app venv instead, update the `python` field in each entry.

---

## Step 7: Verify Everything Is Running

| Terminal | Service | Expected log line | URL |
|----------|---------|-------------------|-----|
| 1 | Chat backend | `Uvicorn running on http://127.0.0.1:8001` | http://127.0.0.1:8001/docs |
| 2 | Chat frontend | `Local:   http://localhost:3001/` | http://localhost:3001 |
| 3 | Scenario backend | `Uvicorn running on http://127.0.0.1:8000` | http://127.0.0.1:8000/docs |
| 4 | Scenario frontend | `Local:   http://localhost:5173/` | http://localhost:5173 |

**Quick health checks:**

```bash
curl http://127.0.0.1:8001/health   # Chat backend
curl http://127.0.0.1:8000/health   # Scenario backend
```

Open http://localhost:5173 in a browser to load the scenario host UI (with the embedded chat widget), or http://localhost:3001 for the standalone chat UI.

### Common issues

- **Port already in use** — another process is on `8000`/`8001`/`3001`/`5173`. Change the `--port` flag or the Vite `server.port` in `vite.config.ts`.
- **`DefaultAzureCredential` errors** — run `az login`, confirm `az account show` returns the right subscription, and confirm `APP_ENV=dev` is set in the backend `.env`.
- **Frontend gets CORS errors** — ensure both frontend origins (`http://localhost:3001`, `http://localhost:5173`) are in the backend's `ALLOWED_ORIGINS_STR`.
- **Chat responses return errors about missing agents** — you have not populated `FOUNDRY_CHAT_AGENT` / `FOUNDRY_PRODUCT_AGENT` / `FOUNDRY_POLICY_AGENT`. Run the post-provision agent script and copy the names in.

---

## Troubleshooting

### Python version

```bash
python3 --version           # macOS/Linux
python --version            # Windows
```

If Python 3.11+ is missing:

- Ubuntu: `sudo apt install python3.11`
- macOS: `brew install python@3.11`
- Windows: `winget install Python.Python.3.11`

### Recreate the virtual environment

```bash
# From repo root
rm -rf .venv                        # macOS/Linux
Remove-Item -Recurse -Force .venv   # Windows PowerShell

python -m venv .venv
# Activate (see § 6.1) then reinstall requirements
pip install -r chat-app/backend/requirements.txt
pip install -r scenario-app/backend/requirements.txt
```

### PowerShell execution policy (Windows)

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Environment variables not picked up

```bash
# macOS/Linux
env | grep AZURE

# Windows PowerShell
Get-ChildItem Env:AZURE*
```

Confirm each backend `.env` file has real values (not the placeholders from `env.sample`) and that the backend was started from the directory containing its `.env`.

---

## Related Documentation

- [Deployment Guide](./DeploymentGuide.md)
- [Scenario-based Deployment](./scenario-deployment-guide.md)
- [Technical Architecture](./TechnicalArchitecture.md)
- [App Authentication Setup](./AppAuthentication.md)
- [Customizing AZD Parameters](./CustomizingAzdParameters.md)
