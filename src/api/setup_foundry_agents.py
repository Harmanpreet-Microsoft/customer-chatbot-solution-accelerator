import argparse
import sys
import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureAISearchTool
from azure.identity import DefaultAzureCredential
from app.agent_instructions import (
    ORCHESTRATOR_INSTRUCTIONS,
    PRODUCT_LOOKUP_INSTRUCTIONS,
    ORDER_STATUS_INSTRUCTIONS,
    KNOWLEDGE_AGENT_INSTRUCTIONS,
)

PRODUCT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search products with hybrid AI Search + Cosmos DB for maximum speed and accuracy",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for products"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_fast",
            "description": "Ultra-fast product search for quick responses",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for products"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_by_id",
            "description": "Get a specific product by its ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The product ID to look up"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_by_category",
            "description": "Get products by category",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Product category to filter by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 5)",
                        "default": 5
                    }
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_products",
            "description": "Get all available products",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 10)",
                        "default": 10
                    }
                },
                "required": []
            }
        }
    }
]

ORDER_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get complete order details by order ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to retrieve"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "List recent orders for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID to get orders for"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of orders to return (default 10)",
                        "default": 10
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get just the status of an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check status for"
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_refund",
            "description": "Process a refund request for an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to process refund for"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the refund"
                    }
                },
                "required": ["order_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "process_return",
            "description": "Process a return request for an order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to process return for"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for the return"
                    }
                },
                "required": ["order_id", "reason"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_returnable_orders",
            "description": "Get orders within 30-day return window for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID to get returnable orders for"
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders_by_date_range",
            "description": "Get orders from last N days for a customer (default 180 days)",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID to get orders for"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back (default 180)",
                        "default": 180
                    }
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_if_returnable",
            "description": "Check if a specific order is within return window",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID to check"
                    }
                },
                "required": ["order_id"]
            }
        }
    }
]

KNOWLEDGE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup",
            "description": "Search policy documents with enhanced AI Search",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for policy documents"
                    },
                    "top": {
                        "type": "integer",
                        "description": "Number of results to return (default 3)",
                        "default": 3
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_policy",
            "description": "Context-aware policy lookup",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Policy question or query"
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context for the query",
                        "default": ""
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_return_policy",
            "description": "Get return policy information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_shipping_info",
            "description": "Get shipping information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_warranty_info",
            "description": "Get warranty information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

def create_agents(
    foundry_endpoint: str,
    model_name: str = "gpt-4o-mini",
    solution_name: str = "ecommerce"
):
    print(f"🚀 Creating Azure AI Foundry agents for {solution_name}")
    print(f"📍 Endpoint: {foundry_endpoint}")
    print(f"🤖 Model: {model_name}\n")
    
    credential = DefaultAzureCredential()
    
    project_client = AIProjectClient(
        endpoint=foundry_endpoint,
        credential=credential,
    )
    
    with project_client:
        agents_client = project_client.agents
        
        print("1️⃣  Creating Orchestrator Agent...")
        orchestrator_agent = agents_client.create_agent(
            model=model_name,
            name=f"OrchestratorAgent-{solution_name}",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
        )
        print(f"   ✅ Created: {orchestrator_agent.name}")
        print(f"   ID: {orchestrator_agent.id}\n")
        
        print("2️⃣  Creating Product Lookup Agent...")
        product_agent = agents_client.create_agent(
            model=model_name,
            name=f"ProductLookupAgent-{solution_name}",
            instructions=PRODUCT_LOOKUP_INSTRUCTIONS,
            tools=PRODUCT_TOOLS
        )
        print(f"   ✅ Created: {product_agent.name}")
        print(f"   ID: {product_agent.id}")
        print(f"   Tools: {len(PRODUCT_TOOLS)} functions registered\n")
        
        print("3️⃣  Creating Order Status Agent...")
        order_agent = agents_client.create_agent(
            model=model_name,
            name=f"OrderStatusAgent-{solution_name}",
            instructions=ORDER_STATUS_INSTRUCTIONS,
            tools=ORDER_TOOLS
        )
        print(f"   ✅ Created: {order_agent.name}")
        print(f"   ID: {order_agent.id}")
        print(f"   Tools: {len(ORDER_TOOLS)} functions registered\n")
        
        print("4️⃣  Creating Knowledge Agent...")
        knowledge_agent = agents_client.create_agent(
            model=model_name,
            name=f"KnowledgeAgent-{solution_name}",
            instructions=KNOWLEDGE_AGENT_INSTRUCTIONS,
            tools=KNOWLEDGE_TOOLS
        )
        print(f"   ✅ Created: {knowledge_agent.name}")
        print(f"   ID: {knowledge_agent.id}")
        print(f"   Tools: {len(KNOWLEDGE_TOOLS)} functions registered\n")
        
        print("=" * 70)
        print("🎉 All agents created successfully!")
        print("=" * 70)
        print("\n📋 Copy these values to your .env file:\n")
        print(f"AZURE_FOUNDRY_ENDPOINT={foundry_endpoint}")
        print(f"FOUNDRY_ORCHESTRATOR_AGENT_ID={orchestrator_agent.id}")
        print(f"FOUNDRY_PRODUCT_AGENT_ID={product_agent.id}")
        print(f"FOUNDRY_ORDER_AGENT_ID={order_agent.id}")
        print(f"FOUNDRY_KNOWLEDGE_AGENT_ID={knowledge_agent.id}")
        print(f"USE_FOUNDRY_AGENTS=true")
        print("\n" + "=" * 70)
        
        return {
            "orchestrator": orchestrator_agent.id,
            "product": product_agent.id,
            "order": order_agent.id,
            "knowledge": knowledge_agent.id,
        }

def main():
    parser = argparse.ArgumentParser(
        description="Create Azure AI Foundry agents for e-commerce chatbot"
    )
    parser.add_argument(
        "--foundry-endpoint",
        required=True,
        help="Azure AI Foundry project endpoint (e.g., https://your-project.api.azureml.ms)",
    )
    parser.add_argument(
        "--model-name",
        default="gpt-4o-mini",
        help="Model deployment name (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--solution-name",
        default="ecommerce",
        help="Solution name prefix for agents (default: ecommerce)",
    )
    
    args = parser.parse_args()
    
    try:
        agent_ids = create_agents(
            foundry_endpoint=args.foundry_endpoint,
            model_name=args.model_name,
            solution_name=args.solution_name,
        )
        
        print("\n✅ Setup complete! Next steps:")
        print("1. Copy the environment variables above to your .env file")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Run the backend: uvicorn app.main:app --reload")
        print("4. Test the Foundry integration: python test_foundry_integration.py")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error creating agents: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're logged in: az login")
        print("2. Verify the Foundry endpoint is correct")
        print("3. Check you have permissions to create agents in the project")
        sys.exit(1)

if __name__ == "__main__":
    main()


