#!/usr/bin/env python3
"""
Create Azure AI Foundry agents programmatically using the new Agent Service API.
"""
import asyncio
import logging

from azure.ai.projects.models import PromptAgentDefinition

# Set up logging
logging.basicConfig(level=logging.INFO)


async def create_assistants():
    print("Creating agents in Azure AI Foundry project...")

    try:
        from config import settings
        from foundry_client import get_foundry_client, init_foundry_client

        # Initialize Foundry client
        print("Initializing Foundry client...")
        await init_foundry_client()
        client = get_foundry_client()

        # Define agents to create
        agents_to_create = [
            {
                "name": "orchestrator-agent",
                "description": "Main orchestrator that routes customer inquiries to specialized agents for product searches, order tracking, and policy questions.",
                "instructions": """You are the main orchestrator for Contoso Paints e-commerce customer service. Your role is to:

1. Analyze customer inquiries and route them to appropriate specialists
2. Handle general questions and greetings
3. Provide comprehensive assistance using available tools
4. Maintain a helpful, professional tone

You have access to tools for:
- Product search and recommendations
- Order tracking and management
- Policy and FAQ information

Always aim to provide accurate, helpful responses while maintaining excellent customer service.""",
                "model": "gpt-4o-mini",
            },
            {
                "name": "product-lookup-agent",
                "description": "Specialized agent for product searches, recommendations, and catalog inquiries.",
                "instructions": """You are a product specialist for Contoso Paints e-commerce. Your expertise includes:

1. Product search and discovery
2. Product recommendations based on customer needs
3. Pricing and availability information
4. Product specifications and details
5. Category browsing and filtering

Always help customers find the right products for their needs. Use the product search tools to provide accurate, up-to-date information.""",
                "model": "gpt-4o-mini",
            },
            {
                "name": "order-status-agent",
                "description": "Specialized agent for order tracking, status updates, and order management.",
                "instructions": """You are an order specialist for Contoso Paints e-commerce. You help customers with:

1. Order status and tracking
2. Order history and details
3. Return and refund requests
4. Shipping information
5. Order modifications when possible

Always provide accurate order information and help resolve any order-related concerns professionally.""",
                "model": "gpt-4o-mini",
            },
            {
                "name": "knowledge-agent",
                "description": "Specialized agent for policies, FAQs, warranties, and general support information.",
                "instructions": """You are a knowledge specialist for Contoso Paints e-commerce. You provide information about:

1. Return and refund policies
2. Warranty information
3. Shipping policies
4. FAQs and general questions
5. Company policies and procedures

Always provide accurate, helpful information from official policies and documentation.""",
                "model": "gpt-4o-mini",
            },
        ]

        created_agents = []

        for agent_config in agents_to_create:
            print(f"\nCreating {agent_config['name']}...")

            try:
                # Create agent version using new API
                agent = await client.agents.create_version(
                    agent_name=agent_config["name"],
                    definition=PromptAgentDefinition(
                        model=agent_config["model"],
                        instructions=agent_config["instructions"],
                        tools=[],
                    ),
                )

                print(f"Created {agent.name}")
                print(f"   Name: {agent.name}")
                print(f"   Version: {agent.version}")

                created_agents.append(
                    {
                        "name": agent_config["name"],
                        "version": agent.version,
                        "role": agent_config["name"].replace("-", "_"),
                    }
                )

            except Exception as e:
                print(f"Failed to create {agent_config['name']}: {e}")

        # Print environment variable updates
        if created_agents:
            print("\nUpdate your .env file with these agent names:")
            print("=" * 60)

            env_mapping = {
                "orchestrator_agent": "FOUNDRY_ORCHESTRATOR_AGENT_ID",
                "product_lookup_agent": "FOUNDRY_PRODUCT_AGENT_ID",
                "order_status_agent": "FOUNDRY_ORDER_AGENT_ID",
                "knowledge_agent": "FOUNDRY_KNOWLEDGE_AGENT_ID",
            }

            for agent in created_agents:
                role = agent["role"]
                if role in env_mapping:
                    env_var = env_mapping[role]
                    print(f'{env_var}="{agent["name"]}"')

            print("=" * 60)

        return created_agents

    except Exception as e:
        print(f"Failed to create agents: {e}")
        import traceback

        traceback.print_exc()
        return []


if __name__ == "__main__":
    asyncio.run(create_assistants())
