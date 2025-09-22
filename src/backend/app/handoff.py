# Copyright (c) Microsoft. All rights reserved.

import asyncio
import os
import json

from azure.identity import AzureCliCredential, DefaultAzureCredential, get_bearer_token_provider

from semantic_kernel.agents import Agent, ChatCompletionAgent, HandoffOrchestration, OrchestrationHandoffs
from semantic_kernel.agents.runtime import InProcessRuntime
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import AuthorRole, ChatMessageContent, FunctionCallContent, FunctionResultContent
from semantic_kernel.functions import kernel_function

"""
The following sample demonstrates how to create a handoff orchestration that represents
a customer support triage system. The orchestration consists of 4 agents, each specialized
in a different area of customer support: triage, refunds, order status, and order returns.

Depending on the customer's request, agents can hand off the conversation to the appropriate
agent.

Human in the loop is achieved via a callback function similar to the one used in group chat
orchestration. Except that in the handoff orchestration, all agents have access to the
human response function, whereas in the group chat orchestration, only the manager has access
to the human response function.

This sample demonstrates the basic steps of creating and starting a runtime, creating
a handoff orchestration, invoking the orchestration, and finally waiting for the results.
"""


class OrderStatusPlugin:
    @kernel_function
    def search_orders(self, order_id: str = None, product_id: str = None, description: str = None, top: int = 5) -> str:
        """Search orders by order ID, product ID, or description (JSON array as string)."""
        try:
            from .services import cosmos
        except Exception as ex:
            return json.dumps({"error": f"Order search unavailable (import error: {ex})"})
        try:
            items = cosmos.search_orders(order_id=order_id, product_id=product_id, description=description, top=top)
        except Exception as ex:
            return json.dumps({"error": f"Failed to search orders: {ex}"})
        def _map(doc: dict) -> dict:
            order_obj = doc.get("order") or {}
            return {
                "id": doc.get("id"),
                "customerId": doc.get("customerId") or order_obj.get("customerId"),
                "productId": doc.get("productId") or doc.get("productid") or order_obj.get("productId"),
                "price": doc.get("price") or order_obj.get("price") or doc.get("total") or order_obj.get("total"),
                "quantity": doc.get("quantity") or order_obj.get("quantity"),
                "status": doc.get("status") or doc.get("state") or order_obj.get("status"),
                "description": doc.get("description") or order_obj.get("description"),
                "createdAt": doc.get("createdAt") or doc.get("timestamp") or order_obj.get("createdAt"),
            }
        mapped = [_map(d) for d in items]
        if not mapped:
            return "No matching orders found.\n[]"
        lines = []
        for m in mapped:
            bits = [f"status={m.get('status')}"]
            if m.get('productId') is not None:
                bits.append(f"product={m.get('productId')}")
            if m.get('quantity') is not None:
                bits.append(f"qty={m.get('quantity')}")
            if m.get('price') is not None:
                bits.append(f"price={m.get('price')}")
            lines.append(f"Order {m.get('id')}: " + ", ".join(bits))
        return "\n".join(lines) + "\n" + json.dumps(mapped)
    @kernel_function
    def check_order_status(self, order_id: str) -> str:
        """Look up an order by id in Cosmos DB and return plain text summary PLUS JSON.
        Format:
        Order <id>: status=<status>, product=<productId>, qty=<quantity>, price=<price>
        <JSON object>
        If not found returns a JSON object with message only."""
        try:
            from .services import cosmos  # local import
        except Exception as ex:
            return json.dumps({"error": f"Order lookup unavailable (import error: {ex})"})

        try:
            doc = cosmos.get_order_by_id(order_id)
        except Exception as ex:
            return json.dumps({"error": f"Failed to query order {order_id}: {ex}"})

        if not doc:
            return json.dumps({"message": f"No order found for id {order_id}"})

        order_obj = doc.get("order") or {}
        mapped = {
            "id": doc.get("id"),
            "customerId": doc.get("customerId") or order_obj.get("customerId"),
            "productId": doc.get("productId") or doc.get("productid") or order_obj.get("productId"),
            "price": doc.get("price") or order_obj.get("price") or doc.get("total") or order_obj.get("total"),
            "quantity": doc.get("quantity") or order_obj.get("quantity"),
            "status": doc.get("status") or doc.get("state") or order_obj.get("status"),
            "description": doc.get("description") or order_obj.get("description"),
            "createdAt": doc.get("createdAt") or doc.get("timestamp") or order_obj.get("createdAt"),
        }
        summary_bits = [
            f"status={mapped.get('status')}",
        ]
        if mapped.get('productId') is not None:
            summary_bits.append(f"product={mapped.get('productId')}")
        if mapped.get('quantity') is not None:
            summary_bits.append(f"qty={mapped.get('quantity')}")
        if mapped.get('price') is not None:
            summary_bits.append(f"price={mapped.get('price')}")
        summary_line = f"Order {mapped.get('id')}: " + ", ".join(summary_bits)
        return summary_line + "\n" + json.dumps(mapped)
    @kernel_function
    def list_recent_orders(self, customer_id: str, top: int = 5) -> str:
        """List recent orders for a customer (JSON array as string)."""
        try:
            from .services import cosmos
        except Exception as ex:  # pragma: no cover
            return json.dumps({"error": f"Order listing unavailable (import error: {ex})"})
        try:
            items = cosmos.list_orders_for_customer(customer_id, top=top)
        except Exception as ex:
            return json.dumps({"error": f"Failed to list orders: {ex}"})
        def _map(doc: dict) -> dict:
            order_obj = doc.get("order") or {}
            return {
                "id": doc.get("id"),
                "customerId": doc.get("customerId") or order_obj.get("customerId"),
                "productId": doc.get("productId") or doc.get("productid") or order_obj.get("productId"),
                "price": doc.get("price") or order_obj.get("price") or doc.get("total") or order_obj.get("total"),
                "quantity": doc.get("quantity") or order_obj.get("quantity"),
                "status": doc.get("status") or doc.get("state") or order_obj.get("status"),
                "description": doc.get("description") or order_obj.get("description"),
                "createdAt": doc.get("createdAt") or doc.get("timestamp") or order_obj.get("createdAt"),
            }
        mapped = [_map(d) for d in items]
        if not mapped:
            return f"No recent orders found for customer {customer_id}.\n[]"
        lines = []
        for m in mapped:
            bits = [f"status={m.get('status')}"]
            if m.get('productId') is not None:
                bits.append(f"product={m.get('productId')}")
            if m.get('quantity') is not None:
                bits.append(f"qty={m.get('quantity')}")
            if m.get('price') is not None:
                bits.append(f"price={m.get('price')}")
            lines.append(f"Order {m.get('id')}: " + ", ".join(bits))
        return "\n".join(lines) + "\n" + json.dumps(mapped)


class OrderRefundPlugin:
    @kernel_function
    def process_refund(self, order_id: str, reason: str) -> str:
        """Process a refund for an order."""
        # Simulate processing a refund
        print(f"Processing refund for order {order_id} due to: {reason}")
        return f"Refund for order {order_id} has been processed successfully."


class OrderReturnPlugin:
    @kernel_function
    def process_return(self, order_id: str, reason: str) -> str:
        """Process a return for an order."""
        # Simulate processing a return
        print(f"Processing return for order {order_id} due to: {reason}")
        return f"Return for order {order_id} has been processed successfully."


class ProductLookupPlugin:
    """Lightweight wrapper around the existing SQL product service for demo agent usage."""

    @kernel_function
    def search_products(self, query: str, top: int = 5) -> str:
        try:
            from .services import sql
        except Exception as ex:  # pragma: no cover
            return json.dumps({"error": f"Product search unavailable (import error: {ex})"})
        try:
            items = sql.search_products(query, limit=top)
        except Exception as ex:
            return json.dumps({"error": f"Failed to search products: {ex}"})
        trimmed = [
            {
                "id": p.get("id"),
                "sku": p.get("sku"),
                "name": p.get("name"),
                "description": p.get("description"),
                "price": p.get("price"),
                "inventory": p.get("inventory"),
            }
            for p in items
        ]
        return json.dumps(trimmed)

    @kernel_function
    def get_by_sku(self, sku: str) -> str:
        try:
            from .services import sql
        except Exception as ex:  # pragma: no cover
            return json.dumps({"error": f"Product lookup unavailable (import error: {ex})"})
        try:
            prod = sql.find_product_by_sku(sku)
        except Exception as ex:
            return json.dumps({"error": f"Failed to lookup product: {ex}"})
        if not prod:
            return json.dumps({"message": f"No product found for SKU {sku}"})
        # Trim description length for brevity
        if prod.get("description") and len(prod["description"]) > 240:
            prod["description"] = prod["description"][:240] + "..."
        return json.dumps(prod)

class ReferenceLookupPlugin:
    """Plugin to query Azure Search for reference, return, and support info."""

    @kernel_function
    def lookup_reference(self, query: str, top: int = 3) -> str:
        try:
            from .services import search
        except Exception as ex:
            return json.dumps({"error": f"Reference search unavailable (import error: {ex})"})
        try:
            hits = search.search_reference(query, top=top)
        except Exception as ex:
            return json.dumps({"error": f"Failed to search reference info: {ex}"})
        # Return compact JSON array of results
        return json.dumps(hits)

def get_agents() -> tuple[list[Agent], OrchestrationHandoffs]:
    """Return a list of agents that will participate in the Handoff orchestration and the handoff relationships.

    Feel free to add or remove agents and handoff connections.
    """
    credential = DefaultAzureCredential()
    token_provider = get_bearer_token_provider(
        credential, "https://cognitiveservices.azure.com/.default"
    )
    print("Using Azure token provider with credential:", credential)

    # Support either AZURE_OPENAI_API_KEY or legacy AZURE_OPENAI_KEY
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    support_agent = ChatCompletionAgent(
        name="TriageAgent",
        description="A customer support agent that triages issues.",
        instructions="Handle customer requests.",
        service=AzureChatCompletion(
            # credential=credential,
            deployment_name=deployment,
            #base_url=endpoint,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            # ad_token_provider=token_provider
        ),
    )

    refund_agent = ChatCompletionAgent(
        name="RefundAgent",
        description="A customer support agent that handles refunds.",
        instructions="Handle refund requests.",
        service=AzureChatCompletion(
            # credential=credential,
            deployment_name=deployment,
            #base_url=endpoint,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            # ad_token_provider=token_provider
        ),
        plugins=[OrderRefundPlugin()],
    )

    order_status_agent = ChatCompletionAgent(
        name="OrderStatusAgent",
        description="A customer support agent that checks order status.",
        instructions=(
            "Handle order status and tracking requests. If the user supplies an order id (numeric or simple token) call check_order_status immediately. "
            "Return BOTH a concise plain text summary line and then a newline and the JSON object from the tool. "
            "For partial info (product id, description keywords) call search_orders and return one summary line per order followed by a newline and the JSON array. "
            "For recent orders scenarios call list_recent_orders and use the same pattern (summary lines, newline, JSON array). "
            "Do NOT wrap or explain beyond that dual-format output."
        ),
        service=AzureChatCompletion(
            # credential=credential,
            deployment_name=deployment,
            #base_url=endpoint,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            # ad_token_provider=token_provider
        ),
        plugins=[OrderStatusPlugin()],
    )

    order_return_agent = ChatCompletionAgent(
        name="OrderReturnAgent",
        description="A customer support agent that handles order returns.",
        instructions="Handle order return requests.",
        service=AzureChatCompletion(
            # credential=credential,
            deployment_name=deployment,
            #base_url=endpoint,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            # ad_token_provider=token_provider
        ),
        plugins=[OrderReturnPlugin()],
    )

    product_lookup_agent = ChatCompletionAgent(
        name="ProductLookupAgent",
        description="Helps users find products by name, description, or SKU.",
        instructions=(
            "When the user asks about products, pricing, availability, or specifies a SKU: "
            "Use get_by_sku if a SKU pattern is detected (alphanumeric token). Otherwise use search_products. "
            "Respond ONLY with the compact JSON array of products found. Do NOT include any summary, explanation, or extra text—just the JSON. "
            "If no products are found, return an empty JSON array []."
        ),
        service=AzureChatCompletion(
            # credential=credential,
            deployment_name=deployment,
            #base_url=endpoint,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            # ad_token_provider=token_provider
        ),
        plugins=[ProductLookupPlugin()],
    )

    reference_lookup_agent = ChatCompletionAgent(
        name="ReferenceLookupAgent",
        description="Answers questions about returns, policies, and support using Azure Search.",
        instructions=(
            "For any question about returns, policies, customer support, or reference info, ALWAYS call lookup_reference with the user's query. "
            "Respond ONLY with the compact JSON array of results. Do NOT include any summary, explanation, or extra text—just the JSON. "
            "If no results are found, return an empty JSON array []."
        ),
        service=AzureChatCompletion(
            deployment_name=deployment,
            endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        ),
        plugins=[ReferenceLookupPlugin()],
    )

    # Define the handoff relationships between agents
    handoffs = (
        OrchestrationHandoffs()
        .add_many(
            source_agent=support_agent.name,
            target_agents={
                refund_agent.name: "Refund related issues",
                order_status_agent.name: "Order status or tracking questions",
                order_return_agent.name: "Order return related issues",
                product_lookup_agent.name: "Product search, SKU, availability, price",
                reference_lookup_agent.name: "Returns, policies, support, reference info",
            },
        )
        .add(
            source_agent=refund_agent.name,
            target_agent=support_agent.name,
            description="Back to triage if not refund related",
        )
        .add(
            source_agent=order_status_agent.name,
            target_agent=support_agent.name,
            description="Back to triage if not status related",
        )
        .add(
            source_agent=order_return_agent.name,
            target_agent=support_agent.name,
            description="Back to triage if not return related",
        )
        .add(
            source_agent=product_lookup_agent.name,
            target_agent=support_agent.name,
            description="Back to triage if not product related",
        )
        .add(
            source_agent=reference_lookup_agent.name,
            target_agent=support_agent.name,
            description="Back to triage if not reference related",
        )
    )

    return [support_agent, refund_agent, order_status_agent, order_return_agent, product_lookup_agent, reference_lookup_agent], handoffs


def agent_response_callback(message: ChatMessageContent) -> None:
    """Observer function to print the messages from the agents.

    Please note that this function is called whenever the agent generates a response,
    including the internal processing messages (such as tool calls) that are not visible
    to other agents in the orchestration.
    """
    print(f"{message.name}: {message.content}")
    for item in message.items:
        if isinstance(item, FunctionCallContent):
            print(f"Calling '{item.name}' with arguments '{item.arguments}'")
        if isinstance(item, FunctionResultContent):
            print(f"Result from '{item.name}' is '{item.result}'")


def human_response_function() -> ChatMessageContent:
    """Observer function to print the messages from the agents."""
    user_input = input("User: ")
    return ChatMessageContent(role=AuthorRole.USER, content=user_input)

class HandoffChatOrchestrator:
    """API wrapper for orchestration: collects all assistant messages and indicates if awaiting user reply."""

    def __init__(self) -> None:
        agents, handoffs = get_agents()
        self._runtime = InProcessRuntime()
        self._runtime.start()

        self._assistant_messages: list[str] = []
        self._last_agent: str | None = None  # Track last agent that prompted for user input

        def _capture_callback(message: ChatMessageContent) -> None:
            agent_response_callback(message)
            if message.content and message.role == AuthorRole.ASSISTANT:
                self._assistant_messages.append(message.content)
                self._last_agent = message.name  # Save agent name

        self.handoff_orchestration = HandoffOrchestration(
            members=agents,
            handoffs=handoffs,
            agent_response_callback=_capture_callback,
        )

    async def respond(self, user_text: str, history: list[dict] | None = None) -> dict:
        # Improve context threading: if last agent prompted, prepend system message to user reply
        self._assistant_messages = []
        if self._last_agent:
            # Prepend a system message to help orchestration route reply to correct agent
            user_text = f"[System: This is a follow-up response for {self._last_agent}. Please continue handling the user's request.]\n{user_text}"
        invoke_kwargs = dict(task=user_text, runtime=self._runtime)
        result = await self.handoff_orchestration.invoke(**invoke_kwargs)
        value = await result.get()
        last_msg = self._assistant_messages[-1] if self._assistant_messages else (value if isinstance(value, str) else str(value))
        awaiting_user = False
        if self._assistant_messages and last_msg.strip().endswith("?"):
            awaiting_user = True
        return {
            "messages": self._assistant_messages if self._assistant_messages else [last_msg],
            "awaiting_user": awaiting_user
        }

    async def shutdown(self):  # optional cleanup hook
        await self._runtime.stop_when_idle()