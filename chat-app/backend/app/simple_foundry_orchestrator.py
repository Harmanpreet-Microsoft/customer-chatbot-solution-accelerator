from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from .config import has_foundry_config, settings
from .foundry_client import get_foundry_client, get_openai_client, init_foundry_client
from .plugins.orders_plugin import OrdersPlugin
from .plugins.reference_plugin import ReferencePlugin

logger = logging.getLogger(__name__)


class ConversationCache(TTLCache):
    """Cache for agent conversations with automatic cleanup"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def expire(self, time=None):
        """Remove expired items"""
        items = super().expire(time)
        for key, conversation_id in items:
            try:
                logger.info(f"Conversation expired from cache: {conversation_id}")
            except Exception as e:
                logger.error(f"Error expiring conversation {conversation_id}: {e}")
        return items

    def popitem(self):
        """Remove item using LRU eviction"""
        key, conversation_id = super().popitem()
        try:
            logger.info(f"Conversation evicted from cache (LRU): {conversation_id}")
        except Exception as e:
            logger.error(f"Error evicting conversation {conversation_id}: {e}")
        return key, conversation_id


async def _build_foundry_agent(
    agent_name: str, display_name: str, plugins: Optional[List] = None
) -> Optional[Dict[str, Any]]:
    """Build a Foundry agent reference using the new Agent Service API."""
    try:
        logger.info(f"Building {display_name} (name: {agent_name}) using Azure AI Foundry...")

        client = get_foundry_client()

        try:
            # Verify the agent exists by getting its latest version
            agent = await client.agents.get_agent(agent_name=agent_name)
            logger.info(
                f"Successfully verified Foundry agent: {agent.name or display_name}"
            )

            agent_info = {
                "name": agent_name,
                "display_name": display_name,
                "id": getattr(agent, "id", agent_name),
                "plugins": plugins or [],
            }

            return agent_info

        except Exception as e:
            logger.error(f"Failed to verify Foundry agent {display_name}: {e}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"Error building Foundry agent '{display_name}' with name '{agent_name}': {e}")
        return None


class SimpleFoundryOrchestrator:
    """
    Simple orchestrator that routes to the appropriate Foundry agent.
    Uses the new Foundry Agent Service conversations and responses API.
    Includes conversation caching for better performance.
    """

    def __init__(self):
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.is_configured = has_foundry_config()
        self.conversation_cache: ConversationCache = ConversationCache(maxsize=1000, ttl=3600.0)

        if not self.is_configured:
            logger.warning(
                "Foundry not configured. Set AZURE_FOUNDRY_ENDPOINT and agent IDs"
            )

    @classmethod
    async def create(cls) -> "SimpleFoundryOrchestrator":
        """Initialize the orchestrator and create all agents"""
        self = cls()

        if not self.is_configured:
            logger.warning(
                "Simple Foundry orchestrator will not initialize (not configured)"
            )
            return self

        try:
            logger.info("Initializing Simple Foundry orchestrator...")
            logger.info(f"   - Foundry endpoint: {settings.azure_foundry_endpoint}")
            logger.info(
                f"   - Orchestrator agent ID: {settings.foundry_orchestrator_agent_id}"
            )
            logger.info(f"   - Order agent ID: {settings.foundry_order_agent_id}")
            logger.info(
                f"   - Knowledge agent ID: {settings.foundry_knowledge_agent_id}"
            )

            # Initialize Foundry client first
            logger.info("Initializing Foundry client...")
            await init_foundry_client()
            logger.info("Foundry client initialized")

            # Build the main orchestrator agent if configured
            if settings.foundry_orchestrator_agent_id:
                logger.info("Building OrchestratorAgent...")
                orchestrator_agent = await _build_foundry_agent(
                    agent_name=settings.foundry_orchestrator_agent_id,
                    display_name="OrchestratorAgent",
                    plugins=[OrdersPlugin(), ReferencePlugin()],
                )
                if orchestrator_agent:
                    self.agents["OrchestratorAgent"] = orchestrator_agent
                    logger.info("Added OrchestratorAgent with all plugins")
                else:
                    logger.warning("Failed to create OrchestratorAgent")
            else:
                logger.warning("No OrchestratorAgent ID configured")

            # Build agents with their plugins attached
            if settings.foundry_order_agent_id:
                logger.info("Building OrderStatusAgent...")
                order_agent = await _build_foundry_agent(
                    agent_name=settings.foundry_order_agent_id,
                    display_name="OrderStatusAgent",
                    plugins=[OrdersPlugin()],
                )
                if order_agent:
                    self.agents["OrderStatusAgent"] = order_agent
                    logger.info("Added OrderStatusAgent with OrdersPlugin")
                else:
                    logger.warning("Failed to create OrderStatusAgent")
            else:
                logger.warning("No OrderStatusAgent ID configured")

            if settings.foundry_knowledge_agent_id:
                logger.info("Building KnowledgeAgent...")
                knowledge_agent = await _build_foundry_agent(
                    agent_name=settings.foundry_knowledge_agent_id,
                    display_name="KnowledgeAgent",
                    plugins=[ReferencePlugin()],
                )
                if knowledge_agent:
                    self.agents["KnowledgeAgent"] = knowledge_agent
                    logger.info("Added KnowledgeAgent with ReferencePlugin")
                else:
                    logger.warning("Failed to create KnowledgeAgent")
            else:
                logger.warning("No KnowledgeAgent ID configured")

            if not self.agents:
                logger.error("No agents were successfully built!")
                self.is_configured = False
                return self

            logger.info(
                f"Simple Foundry orchestrator initialized with {len(self.agents)} agents"
            )
            return self

        except Exception as e:
            logger.error(
                f"Failed to initialize Simple Foundry orchestrator: {e}",
                exc_info=True,
            )
            self.is_configured = False
            return self

    def _determine_target_agent(self, user_text: str) -> str:
        query_lower = user_text.lower()

        order_patterns = [
            r"\b(order|tracking|shipment|invoice)\b",
            r"\b(where is my|order status|order #)\b",
        ]
        policy_patterns = [
            r"\b(return|refund|exchange|policy|warranty)\b",
            r"\b(problem|issue|complaint|damaged|leaking)\b",
            r"\b(ship|delivery|shipping|track)\b",
            r"\b(help|support|contact|customer service)\b",
            r"\b(guarantee|coverage|defect)\b",
        ]

        order_score = sum(1 for pattern in order_patterns if re.search(pattern, query_lower))
        policy_score = sum(1 for pattern in policy_patterns if re.search(pattern, query_lower))

        if order_score > 0 and "OrderStatusAgent" in self.agents:
            logger.info("Routing to OrderStatusAgent")
            return "OrderStatusAgent"
        if policy_score > 0 and "KnowledgeAgent" in self.agents:
            logger.info("Routing to KnowledgeAgent")
            return "KnowledgeAgent"
        if "OrchestratorAgent" in self.agents:
            logger.info("Default routing to OrchestratorAgent")
            return "OrchestratorAgent"
        available_agents = list(self.agents.keys())
        if available_agents:
            return available_agents[0]
        logger.error("No agents available for routing")
        return "OrchestratorAgent"

    async def respond(
        self,
        user_text: str,
        conversation_id: Optional[str] = None,
        history: List[Dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """Respond using the determined agent with conversation caching"""
        if not self.is_configured:
            logger.error("Simple Foundry orchestrator not configured")
            return {
                "error": "Simple Foundry orchestrator not configured",
                "text": "I'm sorry, the AI service is not properly configured.",
            }

        try:
            # Determine which agent to use
            target_agent_name = self._determine_target_agent(user_text)
            agent_info = self.agents.get(target_agent_name)

            if not agent_info:
                logger.error(f"Agent {target_agent_name} not available")
                return {
                    "error": f"Agent {target_agent_name} not available",
                    "text": f"I'm sorry, the {target_agent_name} is not currently available.",
                }

            logger.info(f"Using {target_agent_name} for query: {user_text[:50]}...")

            openai_client = get_openai_client()
            agent_ref_name = agent_info["name"]

            # Get or create conversation for this session
            foundry_conversation_id = None
            if conversation_id:
                cache_key = f"{conversation_id}_{target_agent_name}"
                foundry_conversation_id = self.conversation_cache.get(cache_key)
                if foundry_conversation_id:
                    logger.info(f"Reusing cached conversation: {foundry_conversation_id}")

            # If no existing conversation, create one
            if not foundry_conversation_id:
                conversation_obj = await openai_client.conversations.create(
                    items=[
                        {
                            "type": "message",
                            "role": "user",
                            "content": user_text,
                        }
                    ],
                )
                foundry_conversation_id = conversation_obj.id
                logger.info(f"Created new conversation: {foundry_conversation_id}")
            else:
                # Add the user message to the existing conversation
                await openai_client.conversations.items.create(
                    conversation_id=foundry_conversation_id,
                    items=[
                        {
                            "type": "message",
                            "role": "user",
                            "content": user_text,
                        }
                    ],
                )

            # Send a response using the agent reference - no polling needed
            response = await openai_client.responses.create(
                input=user_text,
                conversation=foundry_conversation_id,
                extra_body={
                    "agent_reference": {
                        "name": agent_ref_name,
                        "type": "agent_reference",
                    }
                },
            )

            # Cache the conversation for future use
            if conversation_id:
                cache_key = f"{conversation_id}_{target_agent_name}"
                self.conversation_cache[cache_key] = foundry_conversation_id

            # Extract response content - only use the last assistant message
            # (earlier messages may contain intermediate tool call routing text)
            response_content = ""
            for item in reversed(response.output):
                if item.type == "message" and getattr(item, "role", None) == "assistant":
                    for block in item.content:
                        if hasattr(block, "text"):
                            response_content += block.text
                    break  # Only take the last assistant message

            if response_content:
                logger.info(
                    f"{target_agent_name} response length: {len(response_content)} chars"
                )
                return {
                    "messages": [response_content],
                    "awaiting_user": response_content.strip().endswith("?"),
                    "text": response_content,
                }
            else:
                logger.error(f"No response from {target_agent_name}")
                return {
                    "error": "No response from agent",
                    "text": "I'm sorry, I couldn't get a response from the agent.",
                }

        except Exception as e:
            logger.error(f"Error in Simple Foundry orchestrator: {e}", exc_info=True)
            return {
                "error": f"Failed to generate response: {str(e)}",
                "text": "I'm sorry, I encountered an error trying to process your request.",
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
