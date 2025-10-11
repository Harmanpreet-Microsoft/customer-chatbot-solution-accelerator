# Azure AI Foundry Migration Plan
## Migrating `/backend` to Use Remote AI Foundry Agents

### Current State Analysis

**Current `/backend` Architecture:**
- Uses local `ChatCompletionAgent` instances
- Agents defined and run entirely in backend code
- 3 AI strategies: basic, semantic kernel, handoff orchestrator
- No Azure AI Foundry integration
- Traditional app startup (no lifespan management)

**Target `/src/backend` Architecture:**
- Uses remote `AzureAIAgent` instances from Azure AI Foundry
- Agents are defined in Foundry portal, referenced by ID
- Single Foundry-based handoff orchestration
- Foundry client with lifespan management
- Clean separation: backend code vs agent definitions

---

## Migration Strategy Overview

### Phase 1: Add Foundry Infrastructure (No Breaking Changes)
- Add Foundry client management
- Update configuration for Foundry
- Keep existing agents functional

### Phase 2: Create Foundry-Based Orchestrator (Parallel Implementation)
- Implement new Foundry orchestrator alongside existing
- Update plugins for compatibility
- Add feature flag for switching

### Phase 3: Integration & Testing
- Update routers to support both orchestrators
- Add lifespan management to main.py
- Test both implementations

### Phase 4: Cutover & Cleanup
- Switch default to Foundry orchestrator
- Remove old local agent code
- Update documentation

---

## Detailed Implementation Plan

### PHASE 1: Add Foundry Infrastructure

#### Step 1.1: Add Foundry Client Module
**File:** `backend/app/foundry_client.py` (new)

```python
from __future__ import annotations
from typing import Optional
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from .config import settings

_async_cred: Optional[DefaultAzureCredential] = None
_async_client: Optional[AIProjectClient] = None

async def init_foundry_client(endpoint: Optional[str] = None) -> None:
    global _async_cred, _async_client
    if _async_client is not None:
        return
    
    endpoint = endpoint or settings.azure_foundry_endpoint
    if not endpoint:
        raise RuntimeError("AZURE_FOUNDRY_ENDPOINT not configured")
    
    _async_cred = DefaultAzureCredential()
    _async_client = AIProjectClient(endpoint=endpoint, credential=_async_cred)

def get_foundry_client() -> AIProjectClient:
    if _async_client is None:
        raise RuntimeError("Foundry client not initialized. Call init_foundry_client() first.")
    return _async_client

async def shutdown_foundry_client() -> None:
    global _async_client, _async_cred
    if _async_client is not None:
        try:
            await _async_client.close()
        finally:
            _async_client = None
    if _async_cred is not None:
        try:
            await _async_cred.close()
        finally:
            _async_cred = None
```

**Why:** Manages singleton async Foundry client connection with proper lifecycle management.

---

#### Step 1.2: Update Configuration
**File:** `backend/app/config.py`

**Add these fields to Settings class:**
```python
# Azure AI Foundry
azure_foundry_endpoint: Optional[str] = None

# Foundry Agent IDs
foundry_orchestrator_agent_id: str = ""
foundry_product_agent_id: str = ""
foundry_order_agent_id: str = ""
foundry_customer_agent_id: str = ""
foundry_knowledge_agent_id: str = ""

# Feature flags
use_foundry_agents: bool = False  # New flag to switch between local and Foundry
```

**Add helper function:**
```python
def has_foundry_config() -> bool:
    return (
        settings.azure_foundry_endpoint is not None 
        and settings.foundry_orchestrator_agent_id != ""
    )
```

**Update env.example:**
```bash
# Azure AI Foundry
AZURE_FOUNDRY_ENDPOINT=https://your-project.api.azureml.ms
FOUNDRY_ORCHESTRATOR_AGENT_ID=your-orchestrator-id
FOUNDRY_PRODUCT_AGENT_ID=your-product-agent-id
FOUNDRY_ORDER_AGENT_ID=your-order-agent-id
FOUNDRY_CUSTOMER_AGENT_ID=your-customer-agent-id
FOUNDRY_KNOWLEDGE_AGENT_ID=your-knowledge-agent-id
USE_FOUNDRY_AGENTS=false
```

---

#### Step 1.3: Update Dependencies
**File:** `backend/requirements.txt`

**Add:**
```
azure-ai-projects>=1.0.0
azure-identity>=1.15.0
```

---

### PHASE 2: Create Foundry-Based Orchestrator

#### Step 2.1: Create Foundry Orchestrator Module
**File:** `backend/app/foundry_orchestrator.py` (new)

```python
from __future__ import annotations
import logging
from typing import List, Dict, Any, Optional, Tuple
from azure.core.exceptions import ResourceNotFoundError
from semantic_kernel.agents import (
    Agent,
    HandoffOrchestration,
    OrchestrationHandoffs,
    AzureAIAgent,
)
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.contents import (
    AuthorRole,
    ChatMessageContent,
    FunctionCallContent,
    FunctionResultContent,
)
from .config import settings, has_foundry_config
from .foundry_client import get_foundry_client
from .plugins.product_plugin import ProductPlugin
from .plugins.orders_plugin import OrdersPlugin

logger = logging.getLogger(__name__)

async def _resolve_foundry_agent_definition(agent_id: Optional[str], name_fallback: Optional[str] = None):
    client = get_foundry_client()
    definition = None
    
    if agent_id:
        try:
            definition = await client.agents.get_agent(agent_id)
        except ResourceNotFoundError:
            if not name_fallback:
                raise
    
    if definition is None and name_fallback:
        async for a in client.agents.list_agents():
            if a.name == name_fallback:
                definition = a
                break
        if definition is None:
            available = []
            async for a in client.agents.list_agents():
                available.append(f"{a.name} ({a.id})")
            raise ResourceNotFoundError(
                f"Foundry agent not found. Tried id={agent_id!r} and name={name_fallback!r}. "
                f"Available: {', '.join(available) or '(no agents)'}"
            )
    
    if definition is None:
        raise ValueError("No Foundry agent id provided and no name fallback set.")
    return definition

async def _build_foundry_agent(
    *,
    agent_id: str,
    name: str,
    plugins: Optional[List[object]] = None,
    name_fallback: Optional[str] = None,
) -> AzureAIAgent:
    definition = await _resolve_foundry_agent_definition(agent_id, name_fallback)
    client = get_foundry_client()
    return AzureAIAgent(
        client=client,
        definition=definition,
        name=name,
        plugins=plugins or []
    )

async def get_foundry_agents() -> Tuple[List[Agent], OrchestrationHandoffs]:
    orchestrator_id = settings.foundry_orchestrator_agent_id
    if not orchestrator_id:
        raise ValueError("FOUNDRY_ORCHESTRATOR_AGENT_ID must be set")
    
    orchestrator = await _build_foundry_agent(
        agent_id=orchestrator_id,
        name="OrchestratorAgent"
    )
    
    agents: Dict[str, Agent] = {"OrchestratorAgent": orchestrator}
    
    if settings.foundry_product_agent_id:
        product_agent = await _build_foundry_agent(
            agent_id=settings.foundry_product_agent_id,
            name="ProductLookupAgent",
            plugins=[ProductPlugin()],
        )
        agents[product_agent.name] = product_agent
    
    if settings.foundry_order_agent_id:
        order_agent = await _build_foundry_agent(
            agent_id=settings.foundry_order_agent_id,
            name="OrderStatusAgent",
            plugins=[OrdersPlugin()],
        )
        agents[order_agent.name] = order_agent
    
    if settings.foundry_knowledge_agent_id:
        knowledge_agent = await _build_foundry_agent(
            agent_id=settings.foundry_knowledge_agent_id,
            name="KnowledgeAgent",
            plugins=None,
        )
        agents[knowledge_agent.name] = knowledge_agent
    
    members = list(agents.values())
    
    targets = {}
    for name, agent in agents.items():
        if name == orchestrator.name:
            continue
        if name == "ProductLookupAgent":
            targets[name] = "Product search / SKU / availability"
        elif name == "OrderStatusAgent":
            targets[name] = "Order status / history"
        elif name == "KnowledgeAgent":
            targets[name] = "Policies / FAQ / knowledge"
        else:
            targets[name] = name
    
    handoffs = OrchestrationHandoffs()
    if targets:
        handoffs = handoffs.add_many(
            source_agent=orchestrator.name,
            target_agents=targets
        )
        for tgt in targets:
            handoffs = handoffs.add(
                source_agent=tgt,
                target_agent=orchestrator.name,
                description="Back to orchestrator"
            )
    
    return members, handoffs

def agent_response_callback(message: ChatMessageContent) -> None:
    name = message.name or "Agent"
    txt = (message.content or "").strip()
    if txt:
        logger.info(f"[{name}] {txt}")
    for item in message.items:
        if isinstance(item, FunctionCallContent):
            logger.info(f"  -> TOOL CALL: {item.name}({item.arguments})")
        if isinstance(item, FunctionResultContent):
            snippet = (str(item.result) or "")
            if len(snippet) > 400:
                snippet = snippet[:400] + "... [truncated]"
            logger.info(f"  <- TOOL RESULT from {item.name}: {snippet}")

class FoundryOrchestrator:
    def __init__(self):
        self._runtime: InProcessRuntime | None = None
        self._assistant_messages: list[str] = []
        self._last_agent: str | None = None
        self.handoff_orchestration: HandoffOrchestration | None = None
        self.is_configured = has_foundry_config()
    
    @classmethod
    async def create(cls) -> "FoundryOrchestrator":
        self = cls()
        if not self.is_configured:
            logger.warning("Foundry not configured, orchestrator will not initialize")
            return self
        
        members, handoffs = await get_foundry_agents()
        
        self._runtime = InProcessRuntime()
        self._runtime.start()
        
        def _capture(message: ChatMessageContent) -> None:
            agent_response_callback(message)
            if message.content and message.role == AuthorRole.ASSISTANT:
                self._assistant_messages.append(message.content)
                self._last_agent = message.name
        
        self.handoff_orchestration = HandoffOrchestration(
            members=members,
            handoffs=handoffs,
            agent_response_callback=_capture
        )
        logger.info("Foundry orchestrator initialized successfully")
        return self
    
    async def respond(self, user_text: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
        if not self.is_configured or not self._runtime or not self.handoff_orchestration:
            return {"error": "Foundry orchestrator not configured"}
        
        self._assistant_messages = []
        
        if self._last_agent and self._last_agent != "OrchestratorAgent":
            user_text = f"[Follow-up for {self._last_agent}] {user_text}"
        
        result = await self.handoff_orchestration.invoke(
            task=user_text,
            runtime=self._runtime
        )
        value = await result.get()
        
        last_msg = (
            self._assistant_messages[-1]
            if self._assistant_messages
            else (value if isinstance(value, str) else "")
        )
        awaiting_user = bool(last_msg and last_msg.strip().endswith("?"))
        
        return {
            "text": last_msg,
            "messages": self._assistant_messages or ([last_msg] if last_msg else []),
            "awaiting_user": awaiting_user,
        }
    
    async def shutdown(self):
        if self._runtime:
            await self._runtime.stop_when_idle()

_foundry_orchestrator_instance: FoundryOrchestrator | None = None

async def get_foundry_orchestrator() -> FoundryOrchestrator:
    global _foundry_orchestrator_instance
    if _foundry_orchestrator_instance is None:
        _foundry_orchestrator_instance = await FoundryOrchestrator.create()
    return _foundry_orchestrator_instance
```

**Why:** This creates a Foundry-based orchestrator that mirrors the `/src/backend/handoff.py` approach but integrates with the `/backend` structure.

---

#### Step 2.2: Update Plugins for Foundry Compatibility

**Current Issue:** Plugins use synchronous patterns, but Foundry agents work better with async.

**No changes needed immediately** - Semantic Kernel handles sync/async bridging. However, for better performance in Phase 4, consider making plugins async.

---

### PHASE 3: Integration & Testing

#### Step 3.1: Add Lifespan Management to Main
**File:** `backend/app/main.py`

**Replace traditional startup with:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .foundry_client import init_foundry_client, shutdown_foundry_client
from .foundry_orchestrator import get_foundry_orchestrator
from .config import settings, has_foundry_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    if has_foundry_config() and settings.use_foundry_agents:
        await init_foundry_client(settings.azure_foundry_endpoint)
        app.state.foundry_orch = await get_foundry_orchestrator()
    
    try:
        yield
    finally:
        if has_foundry_config() and settings.use_foundry_agents:
            if hasattr(app.state, 'foundry_orch'):
                await app.state.foundry_orch.shutdown()
            await shutdown_foundry_client()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce Chat API with AI-powered customer support",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)
```

---

#### Step 3.2: Update Chat Router
**File:** `backend/app/routers/chat.py`

**Update `generate_ai_response` function:**
```python
async def generate_ai_response(message_content: str, chat_history: List[ChatMessage]) -> str:
    logger.info(f"Generating AI response. Foundry: {settings.use_foundry_agents}, SK: {has_semantic_kernel_config()}")
    
    # Priority 1: Foundry Orchestrator (if enabled)
    if settings.use_foundry_agents and has_foundry_config():
        try:
            from ..foundry_orchestrator import get_foundry_orchestrator
            foundry_orch = await get_foundry_orchestrator()
            ai_response_data = await foundry_orch.respond(
                user_text=message_content,
                history=[{"role": msg.message_type, "content": msg.content} for msg in chat_history[-10:]]
            )
            return ai_response_data.get("text", "I'm sorry, I couldn't process your request.")
        except Exception as e:
            logger.error(f"Error with Foundry orchestrator: {e}")
            # Fall through to next option
    
    # Priority 2: Local Handoff Orchestrator
    if has_semantic_kernel_config() and settings.handoff_orchestration_enabled:
        try:
            handoff_orchestrator = get_handoff_orchestrator()
            ai_response_data = await handoff_orchestrator.respond(
                user_text=message_content,
                history=[{"role": msg.message_type, "content": msg.content} for msg in chat_history[-10:]]
            )
            return ai_response_data.get("text", "I'm sorry, I couldn't process your request.")
        except Exception as e:
            logger.error(f"Error with local handoff orchestrator: {e}")
            # Fall through to next option
    
    # Priority 3: Semantic Kernel (simple routing)
    if has_semantic_kernel_config():
        try:
            semantic_kernel_service = get_semantic_kernel_service()
            ai_response_data = await semantic_kernel_service.respond(
                user_text=message_content,
                history=[{"role": msg.message_type, "content": msg.content} for msg in chat_history[-10:]]
            )
            return ai_response_data.get("text", "I'm sorry, I couldn't process your request.")
        except Exception as e:
            logger.error(f"Error with semantic kernel service: {e}")
    
    # Priority 4: Fallback to basic AI service
    products = await get_db_service().get_products()
    return await ai_service.generate_chat_response(
        user_message=message_content,
        chat_history=chat_history,
        products=products
    )
```

---

#### Step 3.3: Update Health Check
**File:** `backend/app/main.py`

**Update health check endpoint:**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if settings.cosmos_db_endpoint else "mock",
        "openai": "configured" if settings.azure_openai_endpoint else "not_configured",
        "auth": "configured" if settings.azure_client_id else "not_configured",
        "semantic_kernel": "configured" if has_semantic_kernel_config() else "not_configured",
        "handoff_orchestration": "enabled" if (has_semantic_kernel_config() and settings.handoff_orchestration_enabled) else "disabled",
        "foundry": "enabled" if (has_foundry_config() and settings.use_foundry_agents) else "disabled",
        "active_ai": "foundry" if (has_foundry_config() and settings.use_foundry_agents) else 
                     "handoff" if (has_semantic_kernel_config() and settings.handoff_orchestration_enabled) else
                     "semantic_kernel" if has_semantic_kernel_config() else "basic"
    }
```

---

### PHASE 4: Testing Strategy

#### Step 4.1: Create Foundry Test Script
**File:** `backend/test_foundry_integration.py` (new)

```python
import asyncio
import sys
from app.config import settings
from app.foundry_client import init_foundry_client, shutdown_foundry_client
from app.foundry_orchestrator import get_foundry_orchestrator

async def test_foundry_connection():
    print("Testing Foundry connection...")
    try:
        await init_foundry_client(settings.azure_foundry_endpoint)
        print("✓ Foundry client initialized")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize Foundry client: {e}")
        return False

async def test_foundry_orchestrator():
    print("\nTesting Foundry orchestrator...")
    try:
        orchestrator = await get_foundry_orchestrator()
        print("✓ Foundry orchestrator created")
        
        if not orchestrator.is_configured:
            print("✗ Orchestrator not configured")
            return False
        
        print("\nTesting product query...")
        response = await orchestrator.respond("Show me available products")
        print(f"Response: {response.get('text', 'No response')[:200]}...")
        
        print("\nTesting order query...")
        response = await orchestrator.respond("Check order status for order-123")
        print(f"Response: {response.get('text', 'No response')[:200]}...")
        
        return True
    except Exception as e:
        print(f"✗ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("=== Foundry Integration Test ===\n")
    print(f"Foundry Endpoint: {settings.azure_foundry_endpoint}")
    print(f"Orchestrator ID: {settings.foundry_orchestrator_agent_id}")
    print(f"Use Foundry: {settings.use_foundry_agents}\n")
    
    if not settings.azure_foundry_endpoint:
        print("ERROR: AZURE_FOUNDRY_ENDPOINT not set")
        sys.exit(1)
    
    if not settings.foundry_orchestrator_agent_id:
        print("ERROR: FOUNDRY_ORCHESTRATOR_AGENT_ID not set")
        sys.exit(1)
    
    success = True
    
    if not await test_foundry_connection():
        success = False
    
    if success and not await test_foundry_orchestrator():
        success = False
    
    await shutdown_foundry_client()
    
    print("\n" + "="*40)
    if success:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
```

**Run with:**
```bash
cd backend
python test_foundry_integration.py
```

---

#### Step 4.2: Environment Setup for Testing

**Create:** `backend/.env.foundry` (for testing)
```bash
# Copy from .env
# Then add:
AZURE_FOUNDRY_ENDPOINT=https://your-foundry-project.api.azureml.ms
FOUNDRY_ORCHESTRATOR_AGENT_ID=your-orchestrator-id
FOUNDRY_PRODUCT_AGENT_ID=your-product-agent-id
FOUNDRY_ORDER_AGENT_ID=your-order-agent-id
FOUNDRY_KNOWLEDGE_AGENT_ID=your-knowledge-agent-id

# Enable Foundry
USE_FOUNDRY_AGENTS=true

# Disable local orchestration
HANDOFF_ORCHESTRATION_ENABLED=false
USE_SIMPLE_ROUTER=false
```

---

#### Step 4.3: Parallel Testing Checklist

Test both implementations work:

**Local Agents (existing):**
```bash
# Set in .env
USE_FOUNDRY_AGENTS=false
HANDOFF_ORCHESTRATION_ENABLED=true

# Run
uvicorn app.main:app --reload
```

**Foundry Agents (new):**
```bash
# Set in .env
USE_FOUNDRY_AGENTS=true
FOUNDRY_ORCHESTRATOR_AGENT_ID=xxx

# Run
uvicorn app.main:app --reload
```

**Test scenarios:**
1. Product search: "Show me laptops"
2. SKU lookup: "Tell me about SKU-12345"
3. Order status: "Check order ORD-123"
4. Policy question: "What's your return policy?"
5. Mixed conversation with context

---

### PHASE 5: Cutover & Cleanup (Optional)

#### Step 5.1: Update Default Configuration
**File:** `backend/app/config.py`

```python
use_foundry_agents: bool = True  # Change default to True
handoff_orchestration_enabled: bool = False  # Disable local by default
```

---

#### Step 5.2: Deprecation Strategy (Gradual)

**Option A: Keep Both (Recommended)**
- Keep both orchestrators
- Use feature flags to switch
- Allows rollback
- Good for gradual migration

**Option B: Remove Local Agents**
- Delete `handoff_orchestrator.py`
- Delete `semantic_kernel_service.py`
- Update routers to only use Foundry
- Simpler codebase

---

## Implementation Checklist

### Phase 1: Infrastructure ✓
- [ ] Create `foundry_client.py`
- [ ] Update `config.py` with Foundry settings
- [ ] Add Foundry agent ID fields
- [ ] Add `use_foundry_agents` flag
- [ ] Update `env.example`
- [ ] Update `requirements.txt`
- [ ] Install new dependencies: `pip install azure-ai-projects`

### Phase 2: Orchestrator ✓
- [ ] Create `foundry_orchestrator.py`
- [ ] Implement `_resolve_foundry_agent_definition`
- [ ] Implement `_build_foundry_agent`
- [ ] Implement `get_foundry_agents`
- [ ] Implement `FoundryOrchestrator` class
- [ ] Add agent response callback
- [ ] Implement `get_foundry_orchestrator` singleton

### Phase 3: Integration ✓
- [ ] Add lifespan management to `main.py`
- [ ] Update `generate_ai_response` in chat router
- [ ] Add Foundry priority to response generation
- [ ] Update health check endpoint
- [ ] Test startup/shutdown lifecycle

### Phase 4: Testing ✓
- [ ] Create `test_foundry_integration.py`
- [ ] Configure Foundry agents in Azure AI Foundry portal
- [ ] Test Foundry connection
- [ ] Test agent resolution
- [ ] Test product queries
- [ ] Test order queries
- [ ] Test knowledge queries
- [ ] Compare responses: local vs Foundry

### Phase 5: Documentation ✓
- [ ] Update README.md with Foundry setup
- [ ] Document environment variables
- [ ] Add Foundry agent setup guide
- [ ] Update deployment docs
- [ ] Add troubleshooting section

---

## Azure AI Foundry Setup (Prerequisites)

Before running the migration, you need agents in Azure AI Foundry:

### 1. Create Azure AI Foundry Project
```bash
# Azure Portal
1. Navigate to Azure AI Foundry
2. Create new project
3. Note the project endpoint (ends with /api/projects/...)
```

### 2. Create Agents in Foundry Portal

**Orchestrator Agent:**
- Name: `OrchestratorAgent`
- Instructions: "You are a routing assistant. Analyze user requests and hand off to appropriate specialists: ProductLookupAgent for products, OrderStatusAgent for orders, KnowledgeAgent for policies."
- Model: GPT-4o or similar
- Tools: Enable function calling

**Product Lookup Agent:**
- Name: `ProductLookupAgent`
- Instructions: "You help users find products. Use the ProductPlugin tools to search and retrieve product information. Always provide friendly, helpful responses."
- Model: GPT-4o or similar
- Tools: Will be provided by ProductPlugin

**Order Status Agent:**
- Name: `OrderStatusAgent`
- Instructions: "You help users check order status. Use OrdersPlugin tools to look up orders. Be helpful and provide clear status updates."
- Model: GPT-4o or similar
- Tools: Will be provided by OrdersPlugin

**Knowledge Agent:**
- Name: `KnowledgeAgent`
- Instructions: "You answer questions about policies, returns, and FAQs. Search the knowledge base and provide accurate information."
- Model: GPT-4o or similar
- Tools: Azure Search (configure in Foundry)

### 3. Copy Agent IDs
After creating agents, copy their IDs from the Foundry portal and add to `.env`

---

## Troubleshooting Guide

### Issue: "Foundry client not initialized"
**Solution:** Ensure lifespan is running and `init_foundry_client()` is called
```python
# Check in logs
# Should see: "Foundry client initialized"
```

### Issue: "Agent not found"
**Solution:** Verify agent IDs in Foundry portal match .env
```bash
# List agents via API to verify
curl -H "Authorization: Bearer $(az account get-access-token --query accessToken -o tsv)" \
  "https://your-project.api.azureml.ms/api/agents"
```

### Issue: "Plugins not working"
**Solution:** Ensure plugins are attached when building agents
```python
# Check in foundry_orchestrator.py
plugins=[ProductPlugin()]  # Must be passed
```

### Issue: "Authentication failed"
**Solution:** Ensure Azure credentials are configured
```bash
az login
az account set --subscription YOUR_SUBSCRIPTION
```

---

## Rollback Plan

If Foundry integration has issues:

1. **Immediate rollback:**
```bash
# Set in .env
USE_FOUNDRY_AGENTS=false
HANDOFF_ORCHESTRATION_ENABLED=true

# Restart app
```

2. **Remove Foundry code:**
```bash
# If needed
git checkout main -- backend/app/foundry_client.py
git checkout main -- backend/app/foundry_orchestrator.py
```

3. **Keep both implementations:**
- Feature flag allows instant switching
- No code removal needed
- Test in production with gradual rollout

---

## Performance Considerations

### Latency Impact
- **Foundry agents:** +50-200ms per request (network call to Foundry)
- **Local agents:** No network overhead
- **Mitigation:** Use Foundry in same region as backend

### Cost Impact
- **Foundry:** Pay for Foundry hosting + token usage
- **Local:** Pay only for token usage
- **Consideration:** Foundry provides better management/monitoring

### Scalability
- **Foundry:** Managed scaling by Azure
- **Local:** Scales with backend instances
- **Benefit:** Foundry allows independent agent scaling

---

## Timeline Estimate

- **Phase 1 (Infrastructure):** 2-4 hours
- **Phase 2 (Orchestrator):** 4-6 hours
- **Phase 3 (Integration):** 2-3 hours
- **Phase 4 (Testing):** 4-8 hours
- **Phase 5 (Cutover):** 1-2 hours

**Total:** 13-23 hours (2-3 days)

---

## Success Criteria

Migration is successful when:

✅ Foundry orchestrator responds to queries
✅ Plugins execute correctly via Foundry agents
✅ Health check shows "foundry: enabled"
✅ Response quality matches or exceeds local agents
✅ No errors in logs during normal operation
✅ Fallback to local agents works if Foundry unavailable
✅ All existing functionality remains working

---

## Next Steps

1. **Review this plan** - Ensure it aligns with your requirements
2. **Setup Azure AI Foundry** - Create project and agents
3. **Start Phase 1** - Add infrastructure code
4. **Test incrementally** - Don't wait until the end
5. **Keep local agents** - Parallel implementation for safety
6. **Gradual rollout** - Use feature flags to test in production

Would you like me to start implementing any phase?


