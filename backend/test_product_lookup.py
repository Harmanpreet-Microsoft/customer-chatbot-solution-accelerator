#!/usr/bin/env python3
"""
Test script to verify ProductLookupAgent can retrieve products from Cosmos DB
"""
import asyncio
import os
from app.foundry_client import init_foundry_client
from app.foundry_orchestrator import get_foundry_orchestrator
from app.config import settings

# Set the new agent IDs
os.environ["FOUNDRY_ORCHESTRATOR_AGENT_ID"] = "asst_ubY0n5vI6xEztrizZzK1PFIt"
os.environ["FOUNDRY_PRODUCT_AGENT_ID"] = "asst_t5hhMTxAWar91Dm68Xye4lhq"
os.environ["FOUNDRY_ORDER_AGENT_ID"] = "asst_XoJ3LSEGgL1PlAVrVsvp0oPM"
os.environ["FOUNDRY_KNOWLEDGE_AGENT_ID"] = "asst_US1t5FWE7EtMPFx8F6Rb5iyM"

async def test_product_lookup():
    """Test ProductLookupAgent with Cosmos DB"""
    print("🧪 Testing ProductLookupAgent with Cosmos DB...")
    
    try:
        # Initialize Foundry client
        await init_foundry_client()
        print("✅ Foundry client initialized")
        
        # Get orchestrator
        orchestrator = await get_foundry_orchestrator()
        print(f"✅ Orchestrator configured: {orchestrator.is_configured}")
        
        # Test messages that should trigger ProductLookupAgent
        test_messages = [
            "Show me available paint products",
            "Tell me about Dusty Rose",
            "What products do you have in the Paint Shades category?",
            "Find me products with 'forest' in the name"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n📤 Test {i}: '{message}'")
            
            try:
                response = await orchestrator.respond(user_text=message)
                
                if "error" in response:
                    print(f"❌ Error: {response['error']}")
                else:
                    text = response.get("text", "")
                    print(f"📥 Response ({len(text)} chars):")
                    print(f"   {text}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ Product lookup test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_product_lookup())

