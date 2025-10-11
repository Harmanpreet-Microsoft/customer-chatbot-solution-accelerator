#!/usr/bin/env python3
"""
Test script to verify the chat API works end-to-end with Foundry agents
"""
import asyncio
import os
import requests
import json

# Set the new agent IDs
os.environ["FOUNDRY_ORCHESTRATOR_AGENT_ID"] = "asst_ubY0n5vI6xEztrizZzK1PFIt"
os.environ["FOUNDRY_PRODUCT_AGENT_ID"] = "asst_t5hhMTxAWar91Dm68Xye4lhq"
os.environ["FOUNDRY_ORDER_AGENT_ID"] = "asst_XoJ3LSEGgL1PlAVrVsvp0oPM"
os.environ["FOUNDRY_KNOWLEDGE_AGENT_ID"] = "asst_US1t5FWE7EtMPFx8F6Rb5iyM"

async def test_chat_api():
    """Test the chat API with Foundry agents"""
    print("🧪 Testing Chat API with Foundry Agents...")
    
    base_url = "http://localhost:8000"
    
    # Test messages
    test_messages = [
        "Show me available paint products",
        "Tell me about Dusty Rose",
        "What's your return policy?",
        "What's the status of order ORD-123?"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📤 Test {i}: '{message}'")
        
        try:
            # Send message to chat API
            response = requests.post(
                f"{base_url}/api/chat/message",
                json={
                    "content": message,
                    "message_type": "user"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"📥 Response ({len(data.get('content', ''))} chars):")
                print(f"   {data.get('content', '')}")
            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error: Make sure the backend is running on localhost:8000")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n✅ Chat API test completed!")

if __name__ == "__main__":
    asyncio.run(test_chat_api())

