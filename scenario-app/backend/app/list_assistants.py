#!/usr/bin/env python3
"""
List all agents in Azure AI Foundry project using the new Agent Service API.
"""
import asyncio
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)


async def list_assistants():
    print("Listing agents in Azure AI Foundry project...")

    try:
        from foundry_client import get_foundry_client, init_foundry_client

        # Initialize Foundry client
        print("Initializing Foundry client...")
        await init_foundry_client()
        client = get_foundry_client()

        # List all agents using the new API
        print("Fetching agents...")
        agents = await client.agents.list_agents()

        agent_list = []
        async for agent in agents:
            agent_list.append(agent)

        print(f"\nFound {len(agent_list)} agents:")
        for agent in agent_list:
            print(f"   - Name: {agent.name or 'No name'}")
            print(f"     ID: {getattr(agent, 'id', 'N/A')}")
            print(f"     Version: {getattr(agent, 'version', 'N/A')}")
            print(f"     Description: {getattr(agent, 'description', 'No description')}")
            print()

        return agent_list

    except Exception as e:
        print(f"Failed to list agents: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(list_assistants())
