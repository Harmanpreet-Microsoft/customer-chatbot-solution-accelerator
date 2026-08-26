# Scenario-based deployment

Deploy one scenario per azd environment. The default scenario is **ecommerce** (Contoso Paints retail host + embedded chat widget).

## Quick start

```powershell
# Ecommerce (default)
azd env new contoso-ecommerce
azd up

# Healthcare
azd env new contoso-health
azd env set AZURE_ENV_SCENARIO healthcare
azd up

# Banking
azd env new contoso-bank
azd env set AZURE_ENV_SCENARIO banking
azd up
```

Set `AZURE_ENV_SCENARIO` **before the first `azd up`** on a new environment. It drives Bicep (`DEPLOYMENT_SCENARIO`, search indexes, welcome copy, Foundry tool names) and postprovision (data seed, agents, `VITE_SCENARIO` build arg).

Optional preflight:

```powershell
. .\infra\scripts\post-provision\sync_azd_hook_env.ps1
Sync-AzdHookEnv -ProjectRoot (Get-Location)
. .\infra\scripts\pre-provision\preflight_scenario.ps1
```

## What changes per scenario

| Layer | Behavior |
|-------|----------|
| Host UI (`scenario-app/frontend`) | Product grid, hospital services, or banking products |
| Host API | `/api/products` (retail), `/api/services` + `/api/appointments` (healthcare), `/api/accounts` + `/api/banking/transactions` (banking) |
| Chat widget UI | Same layout; welcome text from `/api/chat/config` |
| Foundry agents | Scenario instructions + Search indexes from `scenarios/{scenario}/` |
| Cosmos / Search seed | Scenario catalog CSV + policy docs loaded on postprovision |

## Scenario packs

```
scenarios/
  ecommerce/   # default Contoso Paints
  healthcare/  # Contoso Health
  banking/     # Contoso Bank
```

Each pack contains:

- `manifest.json` — index names, branding, welcome copy
- `data/catalog.csv` — catalog seeded to Cosmos + Search
- `data/policies/` — RAG policy documents
- `agents/*.txt` — Foundry agent instructions

## Infrastructure

- `AZURE_ENV_SCENARIO` flows through [`infra/main.parameters.json`](../infra/main.parameters.json) → Bicep `deploymentScenario`
- App Settings: `DEPLOYMENT_SCENARIO`, `VITE_SCENARIO`, `CHAT_WELCOME_*`, Search index names, `FOUNDRY_CATALOG_TOOL_NAME`, `FOUNDRY_POLICY_TOOL_NAME`
- Foundry agents and chat runtime use matching tool names from `scenarios/{scenario}/manifest.json`
- Scenario host frontend picks up the scenario at runtime via the `VITE_SCENARIO` / `DEPLOYMENT_SCENARIO` App Settings (see [`scenario-app/frontend/startup.sh`](../scenario-app/frontend/startup.sh))

## Switching scenarios

Use a **separate azd environment** per scenario. Reusing an environment requires:

1. `azd env set AZURE_ENV_SCENARIO <scenario>`
2. Re-run postprovision data/agent scripts or full `azd up`
3. Rebuild the scenario host frontend image so `VITE_SCENARIO` is baked in

## Sample chat prompts

**Ecommerce:** "What is your return policy?" / "Show me warm white paint colors"

**Healthcare:** "What are visiting hours?" / "Tell me about primary care services"

**Banking:** "What savings options are available?" / "Show me the credit cards you offer"
