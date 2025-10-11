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
os.environ["FOUNDRY_ORCHESTRATOR_AGENT_ID"] = "asst_0DItElLLjymEUXVUAisyLNcB"
os.environ["FOUNDRY_PRODUCT_AGENT_ID"] = "asst_NLWj1PDQvvb83FruWrnkKeZy"
os.environ["FOUNDRY_ORDER_AGENT_ID"] = "asst_bzRgRxos04LvimCM58JnleZ3"
os.environ["FOUNDRY_KNOWLEDGE_AGENT_ID"] = "asst_t3JKMCpjIhnjmrKx3A9Dh1Y8"

async def test_new_agents():
    """Test the new Foundry agents"""
    print("🧪 Testing New Foundry Agents...")
    
    try:
        # Initialize Foundry client
        await init_foundry_client()
        print("✅ Foundry client initialized")
        
        # Get orchestrator
        orchestrator = await get_foundry_orchestrator()
        print(f"✅ Orchestrator configured: {orchestrator.is_configured}")
        
        # Test messages
        test_messages = [
            "Show me available laptops",
            "What's the status of order ORD-123?",
            "What's your return policy?"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📤 Test {i}: '{message}'")
            
            try:
                response = await orchestrator.respond(user_text=message)
                
                if "error" in response:
                    print(f"❌ Error: {response['error']}")
                else:
                    text = response.get("text", "")
                    print(f"📥 Response ({len(text)} chars): {text[:100]}{'...' if len(text) > 100 else ''}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
        
        print("\n✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_agents())

