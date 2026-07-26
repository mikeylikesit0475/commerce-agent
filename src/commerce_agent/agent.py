import logging
import os

import requests
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types
from litellm.exceptions import APIError

from .prestashop_client import PrestaShopClient

load_dotenv()
logger = logging.getLogger(__name__)

# --- Tool Definitions ---

def get_products(query: str) -> str:
    """
    Searches products in the PrestaShop store catalog by keyword query.
    Use this tool when users ask about product availability, catalog items, pricing, or stock.
    """
    client = PrestaShopClient()
    result = client.get_products(query)
    
    if isinstance(result, dict) and "error" in result:
        return f"Error accessing store: {result['error']}"
    if isinstance(result, dict) and "message" in result:
        return result["message"]
    
    if not isinstance(result, list) or not result:
        return f"No products found matching '{query}'."

    formatted_items = []
    for p in result:
        try:
            price_val = float(p.get('price', 0))
            price_str = f"${price_val:.2f}"
        except (ValueError, TypeError):
            price_str = f"${p.get('price')}"
            
        formatted_items.append(
            f"- {p['name']} (ID: {p['id']}): Price {price_str}, Stock: {p['stock']}. Desc: {str(p.get('description', ''))[:80]}..."
        )
    
    return "Found matching products:\n" + "\n".join(formatted_items)


def get_order_status(order_id: str) -> str:
    """
    Fetches the status, total amount, and item details for a given PrestaShop order ID.
    Use this tool when users ask 'Where is order X?', 'Check status of order #X', or ask about specific orders.
    """
    client = PrestaShopClient()
    clean_id = str(order_id).lstrip('#').strip()
    result = client.get_order(clean_id)
    
    if "error" in result:
        return f"Error fetching order: {result['error']}"
    if "message" in result:
        return result["message"]
        
    items_summary = ", ".join([f"{it['name']} (Qty: {it['quantity']})" for it in result.get("items", [])])
    return (
        f"Order #{result['id']} (Ref: {result['reference']}):\n"
        f"- Status: {result['status']}\n"
        f"- Total Paid: ${float(result['total_paid']):.2f}\n"
        f"- Date Placed: {result['date_add']}\n"
        f"- Items: {items_summary or 'No items listed'}"
    )


def get_inventory_alerts() -> str:
    """
    Fetches active low-stock inventory alerts from the Commerce Core API.
    Use this tool when users ask 'Any inventory alerts?', 'Are any products low in stock?', or ask about stock alerts.
    """
    core_api_url = os.getenv("CORE_API_URL", "http://localhost:5275")
    token = os.getenv("SERVICE_TOKEN")
    if not token:
        return "SERVICE_TOKEN environment variable is not configured."

    try:
        headers = {"Authorization": f"Bearer {token}"}
        alerts_resp = requests.get(f"{core_api_url}/api/alerts", headers=headers, timeout=5)
        if alerts_resp.status_code != 200:
            return f"Core API returned status {alerts_resp.status_code} fetching alerts."
            
        alerts = alerts_resp.json()
        if not alerts:
            return "There are currently no low-stock inventory alerts."
            
        alert_lines = [
            f"- Alert ID {a.get('id')}: Product ID {a.get('productId')} stock dropped to {a.get('stockAtAlert')} (Threshold: {a.get('threshold')})"
            for a in alerts
        ]
        return "Active Inventory Alerts:\n" + "\n".join(alert_lines)
    except requests.RequestException as e:
        return f"Could not connect to Core API for inventory alerts: {e!s}"


def generate_description_copy(product_name: str, current_description: str) -> str:
    """
    Generates an improved marketing description for a product using plain LLM text generation (no tool calling).
    Implemented as part of the architect decision: LLM generates copy, code orchestrates side effects.
    """
    raw_model_name = os.getenv("AGENT_MODEL", "olmo-3.1:32b-instruct")
    if not raw_model_name.startswith("ollama_chat/") and not raw_model_name.startswith("ollama/"):
        model_spec = f"ollama_chat/{raw_model_name}"
    else:
        model_spec = raw_model_name

    model = LiteLlm(model=model_spec)
    copy_agent = Agent(
        name="CopywriterGenerationAgent",
        instruction="You are an expert e-commerce copywriter. Write a compelling, high-converting product description (2-3 sentences max). Return ONLY the product description text, with no preamble or explanation.",
        model=model,
        tools=[]
    )
    session_service = InMemorySessionService()
    runner = Runner(app_name="copywriter_gen_app", agent=copy_agent, session_service=session_service)
    session = session_service.create_session_sync(app_name="copywriter_gen_app", user_id="user_cli")
    
    prompt = f"Write an improved description for this product:\nProduct Name: {product_name}\nCurrent Description: {current_description}"
    message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    
    try:
        events = list(runner.run(user_id="user_cli", session_id=session.id, new_message=message))
        for event in reversed(events):
            if hasattr(event, "content") and event.content and event.content.role == "model":
                text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                if text_parts:
                    return "\n".join(text_parts).strip('"').strip()
    except APIError as e:
        logger.warning(f"Error generating copy via LLM: {e}")

    return f"High performance {product_name} featuring premium quality craftsmanship, modern design, and durable reliability."


# Wrap functions in ADK FunctionTools
catalog_tool = FunctionTool(func=get_products)
order_tool = FunctionTool(func=get_order_status)
alerts_tool = FunctionTool(func=get_inventory_alerts)


def create_router_agent():
    raw_model_name = os.getenv("AGENT_MODEL", "olmo-3.1:32b-instruct")
    if not raw_model_name.startswith("ollama_chat/") and not raw_model_name.startswith("ollama/"):
        model_spec = f"ollama_chat/{raw_model_name}"
    else:
        model_spec = raw_model_name

    model = LiteLlm(model=model_spec)

    agent = Agent(
        name="CommerceRouterAgent",
        instruction="""You are the main customer service and store management assistant for our online store.
        Your job is to understand the user's intent and ALWAYS invoke the appropriate tool:
        1. For ANY product, item, catalog, search, category, stock, or price inquiry (e.g. "Do we sell X?", "Search for X", "List X items", "Check stock for X") -> ALWAYS call get_products with the relevant product or category search query (e.g., query='Books', query='flying cars', query='Home & Garden', query='Clothing').
        2. For ANY order tracking, order status, or order inquiry (e.g. "Where is order X?", "Check status of order #X") -> ALWAYS call get_order_status with the order ID string.
        3. For ANY low stock alerts, inventory warnings, or system alert questions (e.g. "Any inventory alerts?") -> ALWAYS call get_inventory_alerts.
        4. For nonsense, ambiguous, or unclassifiable inputs (e.g. "asdfghjkl", "Hello") -> do NOT invoke any tools. Ask a polite clarifying question.
        Always base your final response strictly on the tool output.
        When a tool returns a status notice or an error message (for example a 'no alerts' notice or a store connection error), repeat that tool message verbatim, word for word, in your final response. Do not paraphrase, shorten, or reword it.""",
        model=model,
        tools=[catalog_tool, order_tool, alerts_tool]
    )
    return agent


def run_agent_query_with_events(query: str):
    """Executes a natural language query through the Router Agent and returns (response_text, events)."""
    session_service = InMemorySessionService()
    
    try:
        agent = create_router_agent()
        runner = Runner(app_name="commerce_router_app", agent=agent, session_service=session_service)
        session = session_service.create_session_sync(app_name="commerce_router_app", user_id="user_cli")
        
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )
        
        events = list(runner.run(user_id="user_cli", session_id=session.id, new_message=message))
        
        # 1. Prefer final model turn (after tool responses) if non-empty and non-tool-call
        response_text = ""
        for event in reversed(events):
            if hasattr(event, "content") and event.content and event.content.role == "model":
                has_func_call = any(hasattr(p, "function_call") and p.function_call for p in event.content.parts)
                text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                if text_parts and not has_func_call:
                    response_text = "\n".join(text_parts)
                    break
        
        # 2. Fallback to tool function_response result if final model text was empty
        if not response_text:
            for event in reversed(events):
                if hasattr(event, "content") and event.content:
                    for p in event.content.parts:
                        if hasattr(p, "function_response") and p.function_response:
                            resp = p.function_response.response
                            if isinstance(resp, dict) and "result" in resp:
                                response_text = str(resp["result"])
                                break
                            if resp:
                                response_text = str(resp)
                                break
                    if response_text:
                        break

        # 3. Fallback to any model text part
        if not response_text:
            for event in reversed(events):
                if hasattr(event, "content") and event.content and event.content.role == "model":
                    text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
                    if text_parts:
                        response_text = "\n".join(text_parts)
                        break

        if not response_text:
            response_text = "I'm sorry, I couldn't process your request."

        return response_text, events
            
    except (APIError, ConnectionError, TimeoutError) as e:
        # Only LLM-provider/connectivity failures degrade to an error string;
        # unexpected exceptions (programming errors) must surface to the caller.
        logger.warning(f"ADK LLM execution fallback due to: {e}")
        return f"Error executing query: {e!s}", []


def run_agent_query(query: str) -> str:
    """Executes a natural language query through the Router Agent and returns text answer."""
    text, _ = run_agent_query_with_events(query)
    return text


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "Any inventory alerts?"
    print(run_agent_query(q))
