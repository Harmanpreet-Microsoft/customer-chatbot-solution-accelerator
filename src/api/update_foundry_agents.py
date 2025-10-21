import os
import sys
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from app.agent_instructions import (
    ORCHESTRATOR_INSTRUCTIONS,
    PRODUCT_LOOKUP_INSTRUCTIONS,
    ORDER_STATUS_INSTRUCTIONS,
    KNOWLEDGE_AGENT_INSTRUCTIONS,
)
from app.config import settings

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

def update_agents():
    if not settings.azure_foundry_endpoint:
        print("AZURE_FOUNDRY_ENDPOINT not configured in environment")
        sys.exit(1)
    
    print(f"Updating Azure AI Foundry agents")
    print(f"Endpoint: {settings.azure_foundry_endpoint}\n")
    
    credential = DefaultAzureCredential()
    
    project_client = AIProjectClient(
        endpoint=settings.azure_foundry_endpoint,
        credential=credential,
    )
    
    with project_client:
        agents_client = project_client.agents
        
        updated_count = 0
        
        if settings.foundry_orchestrator_agent_id:
            print(f"Updating Orchestrator Agent ({settings.foundry_orchestrator_agent_id})...")
            try:
                agents_client.update_agent(
                    agent_id=settings.foundry_orchestrator_agent_id,
                    instructions=ORCHESTRATOR_INSTRUCTIONS,
                )
                print(f"   ✅ Updated instructions\n")
                updated_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
        
        if settings.foundry_product_agent_id:
            print(f"Updating Product Lookup Agent ({settings.foundry_product_agent_id})...")
            try:
                agents_client.update_agent(
                    agent_id=settings.foundry_product_agent_id,
                    instructions=PRODUCT_LOOKUP_INSTRUCTIONS,
                    tools=PRODUCT_TOOLS
                )
                print(f"   ✅ Updated instructions and {len(PRODUCT_TOOLS)} tools\n")
                updated_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
        
        if settings.foundry_order_agent_id:
            print(f"Updating Order Status Agent ({settings.foundry_order_agent_id})...")
            try:
                agents_client.update_agent(
                    agent_id=settings.foundry_order_agent_id,
                    instructions=ORDER_STATUS_INSTRUCTIONS,
                    tools=ORDER_TOOLS
                )
                print(f"   ✅ Updated instructions and {len(ORDER_TOOLS)} tools\n")
                updated_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
        
        if settings.foundry_knowledge_agent_id:
            print(f"Updating Knowledge Agent ({settings.foundry_knowledge_agent_id})...")
            try:
                agents_client.update_agent(
                    agent_id=settings.foundry_knowledge_agent_id,
                    instructions=KNOWLEDGE_AGENT_INSTRUCTIONS,
                    tools=KNOWLEDGE_TOOLS
                )
                print(f"   ✅ Updated instructions and {len(KNOWLEDGE_TOOLS)} tools\n")
                updated_count += 1
            except Exception as e:
                print(f"   ❌ Failed: {e}\n")
        
        print("=" * 70)
        print(f"🎉 Updated {updated_count} agents successfully!")
        print("=" * 70)
        print("\n✅ The agents now have updated instructions and function tools registered.")
        print("🔄 Restart your backend service to pick up the changes.")
        print("\n💡 Note: The tools are now registered with Azure AI Foundry,")
        print("   so agents can call search(), get_order(), lookup(), etc.")

if __name__ == "__main__":
    try:
        update_agents()
        sys.exit(0)
    except Exception as e:
        print(f"\nError updating agents: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure you're logged in: az login")
        print("2. Verify your .env file has all agent IDs configured")
        print("3. Check you have permissions to update agents in the project")
        sys.exit(1)

