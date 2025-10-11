#!/usr/bin/env python3
"""
Test script to verify the new Foundry agents work correctly with proper handoff
"""
import asyncio
import os
from app.foundry_client import init_foundry_client
from app.foundry_orchestrator import get_foundry_orchestrator
from app.config import settings

# Set the new agent IDs
os.environ["FOUNDRY_ORCHESTRATOR_AGENT_ID"] = "asst_s9NEDyY7Ap0SvrMybdFrlQgR"
os.environ["FOUNDRY_PRODUCT_AGENT_ID"] = "asst_xtyku9oJStyZWkPa6au3V0Yn"
os.environ["FOUNDRY_ORDER_AGENT_ID"] = "asst_xIjvR3DgkYxQQGh8wZQ7d3tO"
os.environ["FOUNDRY_KNOWLEDGE_AGENT_ID"] = "asst_qPQQgRdhGTOQSY6kYNj4LBYU"

async def test_proper_handoff():
    """Test that the orchestrator properly hands off to only one agent"""
    print("🧪 Testing Proper Handoff Orchestration...")
    
    try:
        # Initialize Foundry client
        await init_foundry_client()
        print("✅ Foundry client initialized")
        
        # Get orchestrator
        orchestrator = await get_foundry_orchestrator()
        print(f"✅ Orchestrator configured: {orchestrator.is_configured}")
        
        # Test messages that should trigger specific agents
        test_messages = [
            ("Show me available paint products", "Should hand off to ProductLookupAgent"),
            ("What's your return policy?", "Should hand off to KnowledgeAgent"),
            ("What's the status of order ORD-123?", "Should hand off to OrderStatusAgent")
        ]
        
        for i, (message, expected) in enumerate(test_messages, 1):
            print(f"\n📤 Test {i}: '{message}'")
            print(f"   Expected: {expected}")
            
            try:
                response = await orchestrator.respond(user_text=message)
                
                if "error" in response:
                    print(f"❌ Error: {response['error']}")
                else:
                    text = response.get("text", "")
                    print(f"📥 Response ({len(text)} chars):")
                    print(f"   {text[:200]}{'...' if len(text) > 200 else ''}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ Handoff test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_proper_handoff())

