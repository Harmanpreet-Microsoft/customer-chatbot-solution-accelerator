#!/usr/bin/env python3
"""
Simple test to verify the new Simple Foundry Orchestrator works
"""
import asyncio
import os
from app.foundry_client import init_foundry_client
from app.simple_foundry_orchestrator import get_simple_foundry_orchestrator

# Set the agent IDs
os.environ["FOUNDRY_ORCHESTRATOR_AGENT_ID"] = "asst_s9NEDyY7Ap0SvrMybdFrlQgR"
os.environ["FOUNDRY_PRODUCT_AGENT_ID"] = "asst_xtyku9oJStyZWkPa6au3V0Yn"
os.environ["FOUNDRY_ORDER_AGENT_ID"] = "asst_xIjvR3DgkYxQQGh8wZQ7d3tO"
os.environ["FOUNDRY_KNOWLEDGE_AGENT_ID"] = "asst_qPQQgRdhGTOQSY6kYNj4LBYU"

async def test_simple_orchestrator():
    """Test the Simple Foundry Orchestrator"""
    print("🧪 Testing Simple Foundry Orchestrator...")
    
    try:
        # Initialize Foundry client
        await init_foundry_client()
        print("✅ Foundry client initialized")
        
        # Get orchestrator
        orchestrator = await get_simple_foundry_orchestrator()
        print(f"✅ Orchestrator configured: {orchestrator.is_configured}")
        
        # Test a product query
        print(f"\n📤 Testing product query: 'Show me paint products'")
        response = await orchestrator.respond(user_text="Show me paint products")
        
        if "error" in response:
            print(f"❌ Error: {response['error']}")
        else:
            text = response.get("text", "")
            print(f"📥 Response ({len(text)} chars):")
            print(f"   {text[:200]}{'...' if len(text) > 200 else ''}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_orchestrator())

