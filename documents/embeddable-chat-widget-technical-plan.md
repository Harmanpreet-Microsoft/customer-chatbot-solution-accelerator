# Technical plan: embeddable Chat widget (chat-app origins, any-host embed)

This document specifies how to deliver a **small, embeddable client** sourced from **chat-app** capabilities, **without merging** chat and ecommerce repos. Host sites (starting with ecommerce-app, later arbitrary domains) load the widget the same way a third-party would.

Product milestones and roadmap context live in **[customer-chatbot-product-roadmap.md](customer-chatbot-product-roadmap.md)**.

**Progress snapshot (13 May 2026):** Local end-to-end works for the full **chat-app** SPA and for the widget embedded in **ecommerce-app** (script load, Shadow DOM, chat API). Hosted **Azure** path is wired in **`infra_basic`** (widget ships with the chat frontend image; ecommerce gets runtime URLs for widget script + chat API). Remaining gaps vs this plan: **SSE streaming**, **`rid` / OTel embed correlation**, **M4 polish (SRI, iframe fallback)**, and validation that **Foundry agent names** and **Easy Auth cross-origin** behave as expected in production. Details: [§11](#11-implementation-progress-and-deploy-readiness).

## 1. Objectives

- One **distribution artifact** developers can paste into arbitrary HTML (script embed).
- **Runtime configuration** only (API base URL, optional tenant/widget id, theme tokens). No compile-time coupling to ecommerce-app.
- **Security-first**: predictable CORS/auth story, CSP-friendly embedding options, minimized XSS surface.
- **Parity**: reuse chat backend routes already used by full chat SPA (`/api/chat/*`, auth, Voice Live where applicable).
- **Simplicity first**: architecture optimized for demo velocity on Azure App Service.

## 2. Non-goals

- Folding chat UI into ecommerce-app bundles or importing ecommerce source into chat.
- Replacing the full-screen chat SPA except as a **standalone** fallback for unsupported browsers or iframe-blocked contexts.
- Designing full multi-tenant control planes in initial release.
- Introducing Web PubSub, microservices, AKS, Front Door, or distributed session architecture for MVP.

## 3. Embedding model (recommended stack)

Default to one pattern and keep one fallback.

### 3.1 Primary: script loader + Shadow DOM (recommended)

| Concern | How it is addressed |
|--------|----------------------|
| **CSS isolation** | Widget mounts inside a Shadow Root to isolate host CSS and reduce style collisions. |
| **Embed simplicity** | Host adds one script include and calls `ChatWidget.init(...)`. |
| **Debugging** | Single-window runtime avoids cross-window message inspection for initial MVP. |
| **Versioning** | `widget.js` path/version controls rollout; host integration remains stable. |

**Mechanics**

1. Host page loads `https://<widget-host>/widget.js`.
2. `widget.js` creates a host node, attaches Shadow Root, and mounts React app.
3. Widget calls FastAPI APIs on same origin or configured `apiBaseUrl`.

Reference shape:

```text
class ChatWidget {
  init() {
    const host = document.createElement("div")
    document.body.appendChild(host)
    const shadowRoot = host.attachShadow({ mode: "open" })
    createRoot(shadowRoot).render(<App />)
  }
}
window.ChatWidget = new ChatWidget()
```

### 3.2 Fallback: iframe loader (only when required)

Use iframe only if a target host has blocking CSS/policy behavior that Shadow DOM cannot address safely.

## 4. Frontend architecture

```mermaid
flowchart LR
  HostPage[Host ecommerce or external site]
  Loader[widget.js loader]
  Shadow[ShadowRoot React widget]
  Api[chat FastAPI backend]
  HostPage --> Loader
  Loader --> Shadow
  Shadow --> Api
```

**Frontend build targets**

- **Vite library mode** for `widget.js` bundle.
- React + Fluent UI component tree focused on floating launcher + panel.
- No full SPA routing for widget package.

Example embed API:

```html
<script src="https://my-widget.azurewebsites.net/widget.js"></script>
<script>
  ChatWidget.init({
    apiBaseUrl: "https://my-widget.azurewebsites.net",
    theme: "light"
  });
</script>
```

## 5. Backend and CORS contract

Widget backend remains FastAPI.

Primary API scope:

- `POST /api/chat` or streaming equivalent.
- Azure OpenAI orchestration.
- Session state for active widget conversation.

Streaming recommendation:

- Use SSE first (`EventSourceResponse`) instead of WebSockets.
- Keep protocol simple for incremental token streaming.

CORS:

- Explicit host allowlist only.
- No wildcard `*` for credentialed flows.

## 6. Observability and operations

- Widget requests carry **`rid=`** correlation id propagated to OTel **`embed.request_id`**.
- Feature flags (`widget.voice_live.enabled`) backend-driven to avoid mismatched UX.

## 7. Packaging and delivery

| Artifact | Host |
|----------|------|
| `widget.js` | App Service static path (preferred for MVP) |
| static assets (`/assets/*`) | Same App Service as widget backend or widget frontend |
| Integrity | **`SRI hash`** published in README + changelog |

Semantic versioning **`MAJOR`** for breaking **`postMessage`** or config schema.

### Deployment options

Preferred for fastest demo loop:

```text
ai-widget-fastapi-appservice
  -> /widget.js
  -> /assets/*
  -> /api/chat (SSE)
```

Alternative (keep current four-app split):

```text
ResourceGroup
  -> ecommerce-frontend-appservice
  -> ecommerce-backend-fastapi
  -> ai-widget-frontend-appservice
  -> ai-widget-backend-fastapi
```

## 8. Milestones (technical)

Sequencing aligns with later roadmap milestones (**Embed widget MVP** onward) in [customer-chatbot-product-roadmap.md](customer-chatbot-product-roadmap.md).

### M1 Widget shell

- Vite library build for `widget.js`.
- Shadow DOM mount + floating launcher/panel UX.
- Script embed + `ChatWidget.init({ apiBaseUrl, theme })`.

### M2 Backend hardening for third-party origins

- SSE endpoint for streamed responses.
- Explicit origin allowlist and simplified token/session flow.
- Keep auth straightforward for accelerator demo scope.

### M3 ecommerce-app integration PoC

- Add script include to **`ecommerce-app/frontend`** and initialize widget.
- Validate CSS isolation, mobile behavior, and focus/keyboard interactions.

### M4 Polish and CDN

- SRI, minified bundle, Lighthouse budget, error boundary UX.
- Introduce iframe variant only if required by host constraints.

### M5 Extensions

- Optional tenant mapping, partner snippets, and advanced entitlements.
- Defer distributed auth/session patterns until scale requires them.

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Host CSS affects widget | Shadow DOM by default. |
| Cookie SameSite failures | Prefer simple token/session flow; avoid cross-site cookie dependence for MVP. |
| Style drift | Single Fluent theme manifest shared between SPA and widget build (shared token JSON if needed). |

## 10. References in repo

- Chat UI entry: [`chat-app/frontend`](../chat-app/frontend)
- Widget bundle: [`chat-app/frontend/vite.widget.config.ts`](../chat-app/frontend/vite.widget.config.ts), [`chat-app/frontend/src/widget-bootstrap.ts`](../chat-app/frontend/src/widget-bootstrap.ts), [`chat-app/frontend/src/widget.tsx`](../chat-app/frontend/src/widget.tsx), [`chat-app/frontend/src/WidgetApp.tsx`](../chat-app/frontend/src/WidgetApp.tsx)
- Ecommerce embed: [`ecommerce-app/frontend/src/embedChatWidget.ts`](../ecommerce-app/frontend/src/embedChatWidget.ts)
- Separation context: [`src/separationPlan.md`](../src/separationPlan.md)
- Cloud deploy / CORS: [`infra_basic/main.bicep`](../infra_basic/main.bicep) app settings

## 11. Implementation progress and deploy readiness

### 11.1 Where things stand vs milestones

| Milestone | Plan intent | Current state |
|-----------|-------------|---------------|
| **M1 Widget shell** | Vite library `widget.js`, Shadow DOM, `ChatWidget.init`, launcher/panel | **Done.** Second Vite build ([`chat-app/frontend/vite.widget.config.ts`](../chat-app/frontend/vite.widget.config.ts)) outputs IIFE `widget.js` from [`widget-bootstrap.ts`](../chat-app/frontend/src/widget-bootstrap.ts). [`widget.tsx`](../chat-app/frontend/src/widget.tsx) mounts Shadow DOM, inlines CSS, sets API base + embed auth base. [`WidgetApp.tsx`](../chat-app/frontend/src/WidgetApp.tsx) provides floating control + panel and reuses **`ChatSidebar`** (text + voice hooks same as SPA stack). |
| **M2 Backend / third-party** | SSE, explicit CORS, straightforward auth | **Partial.** CORS is explicit (`allow_credentials=True`, no `*`); unified deploy sets chat API **`ALLOWED_ORIGINS_STR`** to **both** chat and ecommerce frontend origins ([`infra_basic/main.bicep`](../infra_basic/main.bicep) chat backend block). Chat still uses **`POST /api/chat/message`** with a **single JSON** assistant reply ([`chat-app/backend/app/routers/chat.py`](../chat-app/backend/app/routers/chat.py)), not **SSE** as recommended in §5. Optional auth path exists; embed uses **`/.auth/me`** on the **widget script origin** ([`AuthContext.tsx`](../chat-app/frontend/src/contexts/AuthContext.tsx) + [`embedContext.ts`](../chat-app/frontend/src/lib/embedContext.ts)). **§6** correlation (**`rid` → `embed.request_id`**) is **not** implemented. |
| **M3 Ecommerce PoC** | Script on ecommerce, validate isolation / mobile / a11y | **Done for integration plumbing.** [`ecommerce-app/frontend/src/embedChatWidget.ts`](../ecommerce-app/frontend/src/embedChatWidget.ts) injects `widget.js`, then calls `ChatWidget.init` with **`VITE_CHAT_API_BASE_URL`** / theme from env or **`window.__RUNTIME_CONFIG__`**. [`main.tsx`](../ecommerce-app/frontend/src/main.tsx) invokes **`embedChatWidget()`**. Dev server serves built `widget.js` from chat `dist` via [`ecommerce-app/frontend/vite.config.ts`](../ecommerce-app/frontend/vite.config.ts). Formal **mobile / keyboard / a11y** sign-off not recorded here. |
| **M4 Polish** | SRI, minify/Lighthouse, iframe fallback | **Not done** (widget build still emits **sourcemaps** in [`vite.widget.config.ts`](../chat-app/frontend/vite.widget.config.ts); no published **SRI** hash; **iframe** loader not built). |
| **M5 Extensions** | Tenants, partner snippets | **Not started.** |

### 11.2 Repo map (implemented pieces)

| Area | Location |
|------|----------|
| Widget library entry + `init` | [`chat-app/frontend/src/widget-bootstrap.ts`](../chat-app/frontend/src/widget-bootstrap.ts) |
| Shadow mount + config | [`chat-app/frontend/src/widget.tsx`](../chat-app/frontend/src/widget.tsx) |
| Widget UI | [`chat-app/frontend/src/WidgetApp.tsx`](../chat-app/frontend/src/WidgetApp.tsx) |
| SPA + widget API base override | [`chat-app/frontend/src/lib/api.ts`](../chat-app/frontend/src/lib/api.ts) |
| Host embed loader | [`ecommerce-app/frontend/src/embedChatWidget.ts`](../ecommerce-app/frontend/src/embedChatWidget.ts) |
| Ecommerce runtime injection (Azure hostnames) | [`ecommerce-app/frontend/startup.sh`](../ecommerce-app/frontend/startup.sh) |
| Chat image includes SPA + `widget.js` | [`chat-app/frontend/Dockerfile`](../chat-app/frontend/Dockerfile) (`npm run build` → `dist/` copied to nginx) |
| Infra: ecommerce → chat widget + API URLs | [`infra_basic/main.bicep`](../infra_basic/main.bicep) (`VITE_CHAT_WIDGET_ORIGIN`, `VITE_CHAT_API_BASE_URL` on ecommerce frontend module) |

### 11.3 Ready to deploy and see it end-to-end?

**You are in good shape to try a hosted run** if images are current and post-provision agent settings are populated: the **same** `npm run build` that the chat frontend Dockerfile already runs produces **`widget.js`** alongside the SPA, and ecommerce startup / Bicep supply the **chat frontend origin** (script) and **chat API base** (XHR).

**Checklist before calling hosted embed “done”:**

1. **Images** — Redeploy **chat-frontend** after any widget change so **`/widget.js`** on the chat site matches the bundle you tested.
2. **Browser network** — From the **ecommerce** origin, confirm **`GET https://<chat-fe>/widget.js`**, then **`POST https://<chat-api>/api/chat/...`** without CORS errors (chat API allowlist already includes **both** frontends in **`infra_basic`**).
3. **AI path** — Chat backend needs working **Foundry** (or equivalent) config for real replies; template leaves agent name env placeholders in some paths—confirm **`FOUNDRY_*_AGENT`** (or your post-provision automation) matches deployed agents.
4. **Auth** — Widget may run as **guest** unless **`fetch` to `https://<chat-fe>/.auth/me`** from the ecommerce page succeeds (cross-origin **cookies + CORS** on the chat App Service). Treat signed-in parity as **environment-dependent** until verified.
5. **Custom domains** — If you move off `*.azurewebsites.net`, update **`ALLOWED_ORIGINS_STR`** and the **`VITE_*`** / runtime URLs accordingly.

**Summary:** Local **M1 + M3** goals are met; **M2** is partially met (CORS yes, SSE and embed **`rid`** no); **M4–M5** are open. You can **deploy and smoke-test** the embed on Azure; treat **streaming**, **observability correlation**, and **M4** items as follow-up work, not blockers for a first **“see it live”** pass.
