from __future__ import annotations
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional
from cachetools import TTLCache

from semantic_kernel.agents import AzureAIAgent, AzureAIAgentThread
from azure.ai.projects.aio import AIProjectClient

from .config import settings, has_foundry_config
from .foundry_client import init_foundry_client, get_foundry_client
from .plugins.product_plugin import ProductPlugin
from .plugins.orders_plugin import OrdersPlugin
from .plugins.reference_plugin import ReferencePlugin

logger = logging.getLogger(__name__)

class ThreadCache(TTLCache):
    """Cache for agent threads with automatic cleanup"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def expire(self, time=None):
        """Remove expired items and delete associated threads"""
        items = super().expire(time)
        for key, thread_id in items:
            try:
                logger.info(f"Thread expired from cache: {thread_id}")
            except Exception as e:
                logger.error(f"Error expiring thread {thread_id}: {e}")
        return items
    
    def popitem(self):
        """Remove item using LRU eviction"""
        key, thread_id = super().popitem()
        try:
            logger.info(f"Thread evicted from cache (LRU): {thread_id}")
        except Exception as e:
            logger.error(f"Error evicting thread {thread_id}: {e}")
        return key, thread_id

async def _resolve_foundry_agent_definition(agent_id: str):
    """Get the agent definition from Foundry"""
    client = get_foundry_client()
    try:
        agent_definition = await client.agents.get_agent(agent_id)
        return agent_definition
    except Exception as e:
        logger.error(f"Error resolving Foundry agent definition for ID '{agent_id}': {e}")
        raise

async def _build_foundry_agent(agent_id: str, name: str, plugins: Optional[List] = None) -> AzureAIAgent:
    """Build an AzureAIAgent from a Foundry agent ID with plugins"""
    definition = await _resolve_foundry_agent_definition(agent_id)
    client = get_foundry_client()
    
    agent = AzureAIAgent(
        client=client,
        definition=definition,
        name=name,
        plugins=plugins or [],
    )
    
    logger.info(f"Built Foundry agent: {name} with {len(plugins or [])} plugins")
    return agent

class SimpleFoundryOrchestrator:
    """
    Simple orchestrator that routes to the appropriate Foundry agent.
    Uses Semantic Kernel AzureAIAgent like the reference implementation.
    Includes thread caching for better performance.
    """

    def __init__(self):
        self.agents: Dict[str, AzureAIAgent] = {}
        self.is_configured = has_foundry_config()
        self.thread_cache: ThreadCache = ThreadCache(maxsize=1000, ttl=3600.0)
        
        if not self.is_configured:
            logger.warning("Foundry not configured. Set AZURE_FOUNDRY_ENDPOINT and agent IDs")
    
    @classmethod
    async def create(cls) -> "SimpleFoundryOrchestrator":
        """Initialize the orchestrator and create all agents"""
        self = cls()
        
        if not self.is_configured:
            logger.warning("Simple Foundry orchestrator will not initialize (not configured)")
            return self
        
        try:
            logger.info("Initializing Simple Foundry orchestrator...")
            logger.info(f"   - Foundry endpoint: {settings.azure_foundry_endpoint}")
            logger.info(f"   - Product agent ID: {settings.foundry_product_agent_id}")
            logger.info(f"   - Order agent ID: {settings.foundry_order_agent_id}")
            logger.info(f"   - Knowledge agent ID: {settings.foundry_knowledge_agent_id}")
            
            # Initialize Foundry client first
            logger.info("Initializing Foundry client...")
            await init_foundry_client()
            logger.info("✅ Foundry client initialized")
            
            # Build agents with their plugins attached
            if settings.foundry_product_agent_id:
                logger.info("Building ProductLookupAgent...")
                product_agent = await _build_foundry_agent(
                    agent_id=settings.foundry_product_agent_id,
                    name="ProductLookupAgent",
                    plugins=[ProductPlugin()]
                )
                self.agents["ProductLookupAgent"] = product_agent
                logger.info("✅ Added ProductLookupAgent with ProductPlugin")
            else:
                logger.warning("⚠️ No ProductLookupAgent ID configured")
            
            if settings.foundry_order_agent_id:
                logger.info("Building OrderStatusAgent...")
                order_agent = await _build_foundry_agent(
                    agent_id=settings.foundry_order_agent_id,
                    name="OrderStatusAgent",
                    plugins=[OrdersPlugin()]
                )
                self.agents["OrderStatusAgent"] = order_agent
                logger.info("✅ Added OrderStatusAgent with OrdersPlugin")
            else:
                logger.warning("⚠️ No OrderStatusAgent ID configured")
            
            if settings.foundry_knowledge_agent_id:
                logger.info("Building KnowledgeAgent...")
                knowledge_agent = await _build_foundry_agent(
                    agent_id=settings.foundry_knowledge_agent_id,
                    name="KnowledgeAgent",
                    plugins=[ReferencePlugin()]
                )
                self.agents["KnowledgeAgent"] = knowledge_agent
                logger.info("✅ Added KnowledgeAgent with ReferencePlugin")
            else:
                logger.warning("⚠️ No KnowledgeAgent ID configured")
            
            if not self.agents:
                logger.error("❌ No agents were successfully built!")
                self.is_configured = False
                return self
            
            logger.info(f"✅ Simple Foundry orchestrator initialized with {len(self.agents)} agents")
            return self
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Simple Foundry orchestrator: {e}", exc_info=True)
            self.is_configured = False
            return self
    
    def _determine_target_agent(self, user_text: str) -> str:
        """Enhanced agent selection with semantic understanding"""
        query_lower = user_text.lower()
        
        # Product-related keywords and patterns
        product_patterns = [
            r'\b(paint|color|blue|red|green|white|black|shade|tone|finish)\b',
            r'\b(product|item|buy|purchase|price|cost)\b',
            r'\b(what.*offer|show.*product|find.*paint)\b',
            r'\b(match.*color|color.*match|sample)\b',
            r'\b(recommend|suggest|help.*choose)\b',
            r'\b(interior|exterior|primer|coating)\b'
        ]
        
        # Policy/support keywords and patterns  
        policy_patterns = [
            r'\b(return|refund|exchange|policy|warranty)\b',
            r'\b(problem|issue|complaint|damaged|leaking)\b',
            r'\b(ship|delivery|shipping|track)\b',
            r'\b(help|support|contact|customer service)\b',
            r'\b(guarantee|coverage|defect)\b',
            r'\b(cancel|order.*status|tracking)\b'
        ]
        
        # Check for product intent
        product_score = sum(1 for pattern in product_patterns if re.search(pattern, query_lower))
        
        # Check for policy intent
        policy_score = sum(1 for pattern in policy_patterns if re.search(pattern, query_lower))
        
        # Special cases
        if any(phrase in query_lower for phrase in ["what products", "what do you offer", "show me products"]):
            logger.info("Routing to ProductLookupAgent - general product inquiry")
            return "ProductLookupAgent"
        
        if any(phrase in query_lower for phrase in ["return policy", "warranty", "refund", "damaged"]):
            logger.info("Routing to KnowledgeAgent - policy inquiry")
            return "KnowledgeAgent"
        
        # Determine primary intent
        if product_score > policy_score:
            logger.info(f"Routing to ProductLookupAgent - product score: {product_score}")
            return "ProductLookupAgent"
        elif policy_score > 0:
            logger.info(f"Routing to KnowledgeAgent - policy score: {policy_score}")
            return "KnowledgeAgent"
        else:
            # Default to product search for general queries
            logger.info("No specific keywords found, defaulting to ProductLookupAgent")
            return "ProductLookupAgent"
    
    async def respond(self, user_text: str, conversation_id: Optional[str] = None, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
        """Respond using the determined agent with thread caching"""
        if not self.is_configured:
            logger.error("Simple Foundry orchestrator not configured")
            return {
                "error": "Simple Foundry orchestrator not configured",
                "text": "I'm sorry, the AI service is not properly configured."
            }
        
        try:
            # Determine which agent to use
            target_agent_name = self._determine_target_agent(user_text)
            agent = self.agents.get(target_agent_name)
            
            if not agent:
                logger.error(f"Agent {target_agent_name} not available")
                return {
                    "error": f"Agent {target_agent_name} not available",
                    "text": f"I'm sorry, the {target_agent_name} is not currently available."
                }
            
            logger.info(f"Using {target_agent_name} for query: {user_text[:50]}...")
            
            # Get or create thread for this conversation (thread caching)
            thread = None
            if conversation_id:
                cache_key = f"{conversation_id}_{target_agent_name}"
                thread_id = self.thread_cache.get(cache_key)
                if thread_id:
                    thread = AzureAIAgentThread(client=agent.client, thread_id=thread_id)
                    logger.info(f"Reusing cached thread: {thread_id}")
            
            # Use the agent's invoke method with thread caching
            response_content = ""
            async for message in agent.invoke(messages=user_text, thread=thread):
                if hasattr(message, 'content') and message.content:
                    response_content += str(message.content)
                
                # Cache the thread for future use
                if conversation_id and hasattr(message, 'thread') and message.thread:
                    cache_key = f"{conversation_id}_{target_agent_name}"
                    self.thread_cache[cache_key] = message.thread.id
            
            if response_content:
                logger.info(f"{target_agent_name} response length: {len(response_content)} chars")
                return {
                    "messages": [response_content],
                    "awaiting_user": response_content.strip().endswith("?"),
                    "text": response_content
                }
            else:
                logger.error(f"No response from {target_agent_name}")
                return {
                    "error": "No response from agent",
                    "text": "I'm sorry, I couldn't get a response from the agent."
                }
                
        except Exception as e:
            logger.error(f"Error in Simple Foundry orchestrator: {e}", exc_info=True)
            return {
                "error": f"Failed to generate response: {str(e)}", 
                "text": "I'm sorry, I encountered an error trying to process your request."
            }

    async def shutdown(self):
        """Cleanup if needed"""
        logger.info("Simple Foundry orchestrator shutdown")

_simple_foundry_orchestrator_instance: SimpleFoundryOrchestrator | None = None

async def get_simple_foundry_orchestrator() -> SimpleFoundryOrchestrator:
    global _simple_foundry_orchestrator_instance
    if _simple_foundry_orchestrator_instance is None:
        _simple_foundry_orchestrator_instance = await SimpleFoundryOrchestrator.create()
    return _simple_foundry_orchestrator_instance
