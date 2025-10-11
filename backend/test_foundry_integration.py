import asyncio
import sys
from app.config import settings, has_foundry_config
from app.foundry_client import init_foundry_client, shutdown_foundry_client
from app.foundry_orchestrator import get_foundry_orchestrator

async def test_foundry_connection():
    print("=" * 70)
    print("🧪 Testing Foundry Connection")
    print("=" * 70)
    print(f"\nFoundry Endpoint: {settings.azure_foundry_endpoint}")
    print(f"Orchestrator ID: {settings.foundry_orchestrator_agent_id}")
    print(f"Product Agent ID: {settings.foundry_product_agent_id or '(not set)'}")
    print(f"Order Agent ID: {settings.foundry_order_agent_id or '(not set)'}")
    print(f"Knowledge Agent ID: {settings.foundry_knowledge_agent_id or '(not set)'}")
    print(f"Use Foundry Agents: {settings.use_foundry_agents}\n")
    
    if not has_foundry_config():
        print("❌ Foundry not configured!")
        print("\nMissing configuration:")
        if not settings.azure_foundry_endpoint:
            print("  - AZURE_FOUNDRY_ENDPOINT")
        if not settings.foundry_orchestrator_agent_id:
            print("  - FOUNDRY_ORCHESTRATOR_AGENT_ID")
        print("\nRun: python setup_foundry_agents.py --foundry-endpoint <endpoint>")
        return False
    
    try:
        await init_foundry_client(settings.azure_foundry_endpoint)
        print("✅ Foundry client initialized successfully\n")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize Foundry client: {e}\n")
        return False

async def test_foundry_orchestrator():
    print("=" * 70)
    print("🤖 Testing Foundry Orchestrator")
    print("=" * 70)
    
    try:
        print("\n1. Creating orchestrator...")
        orchestrator = await get_foundry_orchestrator()
        
        if not orchestrator.is_configured:
            print("❌ Orchestrator not configured\n")
            return False
        
        print("✅ Orchestrator created\n")
        
        test_queries = [
            ("Product search", "Show me available laptops"),
            ("SKU lookup", "Tell me about product SKU-12345"),
            ("Order status", "What's the status of order ORD-123?"),
            ("Policy question", "What's your return policy?"),
        ]
        
        for i, (test_type, query) in enumerate(test_queries, 1):
            print(f"\n{i}. Testing {test_type}...")
            print(f"   Query: '{query}'")
            
            try:
                response = await orchestrator.respond(query)
                
                if "error" in response:
                    print(f"   ❌ Error: {response.get('error')}")
                else:
                    text = response.get("text", "")
                    print(f"   ✅ Response ({len(text)} chars): {text[:150]}...")
                    
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
                return False
        
        print("\n" + "=" * 70)
        print("✅ All orchestrator tests passed!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ Orchestrator test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("\n" + "=" * 70)
    print("🚀 Azure AI Foundry Integration Test")
    print("=" * 70 + "\n")
    
    if not settings.use_foundry_agents:
        print("⚠️  USE_FOUNDRY_AGENTS is set to false")
        print("   Foundry integration is disabled in config")
        print("   Set USE_FOUNDRY_AGENTS=true in .env to enable\n")
    
    success = True
    
    if not await test_foundry_connection():
        success = False
    
    if success:
        if not await test_foundry_orchestrator():
            success = False
    
    await shutdown_foundry_client()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ All tests passed! Foundry integration is working.")
    else:
        print("❌ Some tests failed. Check the errors above.")
    print("=" * 70 + "\n")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


