#!/usr/bin/env python3
"""
Debug script to check Foundry configuration
"""
import os
from app.config import settings, has_foundry_config

print("🔍 Checking Foundry Configuration...")
print("=" * 50)

print(f"AZURE_FOUNDRY_ENDPOINT: {settings.azure_foundry_endpoint}")
print(f"FOUNDRY_ORCHESTRATOR_AGENT_ID: {settings.foundry_orchestrator_agent_id}")
print(f"FOUNDRY_PRODUCT_AGENT_ID: {settings.foundry_product_agent_id}")
print(f"FOUNDRY_ORDER_AGENT_ID: {settings.foundry_order_agent_id}")
print(f"FOUNDRY_KNOWLEDGE_AGENT_ID: {settings.foundry_knowledge_agent_id}")
print(f"USE_FOUNDRY_AGENTS: {settings.use_foundry_agents}")

print("\n" + "=" * 50)
print(f"has_foundry_config(): {has_foundry_config()}")

print("\n" + "=" * 50)
print("Environment Variables:")
for key, value in os.environ.items():
    if 'FOUNDRY' in key or 'AZURE_FOUNDRY' in key or 'USE_FOUNDRY' in key:
        print(f"{key}: {value}")

print("\n" + "=" * 50)
print("✅ Configuration check complete!")
