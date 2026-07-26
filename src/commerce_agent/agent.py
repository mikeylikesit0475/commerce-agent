import logging
import os

from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

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
    # Strip # prefix if provided
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


def update_product_description(product_id: int, new_description: str, confirmed: bool = False) -> str:
    """
    Updates or improves the description of a product in PrestaShop.
    IMPORTANT: Set confirmed=False first to present the proposed draft to the user for review.
    Set confirmed=True ONLY when the user explicitly confirms they want to publish/write the description.
    """
    client = PrestaShopClient()
    prod = client.get_product_by_id(product_id)
    if "error" in prod:
        return f"Error fetching product: {prod['error']}"
    if "message" in prod:
        return prod["message"]

    prod_name = prod.get("name", f"Product #{product_id}")

    if not confirmed:
        return (
            f"[DRAFT DESCRIPTION FOR REVIEW]\n"
            f"Product: {prod_name} (ID: {product_id})\n"
            f"Proposed New Description:\n\"{new_description}\"\n\n"
            f"Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)"
        )

    # Perform actual write-back when confirmed is True
    update_res = client.update_product_description(product_id, new_description)
    if "error" in update_res:
        return f"Failed to update product description: {update_res['error']}"

    # Verify write-back by re-fetching product
    verify_prod = client.get_product_by_id(product_id)
    return (
        f"[PRESTASHOP STORE UPDATED SUCCESSFULLY]\n"
        f"Product: {verify_prod.get('name')} (ID: {product_id})\n"
        f"Stored Description in Database:\n\"{verify_prod.get('description')}\""
    )

# Wrap functions in ADK FunctionTools
catalog_tool = FunctionTool(func=get_products)
order_tool = FunctionTool(func=get_order_status)
copywriter_tool = FunctionTool(func=update_product_description)


# --- Specialist Agents ---

def create_catalog_agent(model):
    return Agent(
        name="CatalogSpecialist",
        instruction="""You are a catalog and product inventory specialist.
        Always call the get_products tool when asked about products, prices, or store inventory.
        Answer based ONLY on the data returned by the tool.""",
        model=model,
        tools=[catalog_tool]
    )

def create_order_agent(model):
    return Agent(
        name="OrderSupportSpecialist",
        instruction="""You are an order support and tracking specialist.
        Always call the get_order_status tool when asked about order status, delivery, or order items.
        Answer based ONLY on the data returned by the tool.""",
        model=model,
        tools=[order_tool]
    )

def create_copywriter_agent(model):
    return Agent(
        name="CopywriterSpecialist",
        instruction="""You are an e-commerce copywriting specialist.
        When asked to draft or update product descriptions, use update_product_description tool with confirmed=False to present a draft.
        Do NOT publish without user confirmation.""",
        model=model,
        tools=[copywriter_tool]
    )

def create_router_agent():
    raw_model_name = os.getenv("AGENT_MODEL", "olmo-3.1:32b-instruct")
    if not raw_model_name.startswith("ollama_chat/") and not raw_model_name.startswith("ollama/"):
        model_spec = f"ollama_chat/{raw_model_name}"
    else:
        model_spec = raw_model_name

    model = LiteLlm(model=model_spec)

    # Multi-tool Router Agent with access to all specialist tools
    agent = Agent(
        name="CommerceRouterAgent",
        instruction="""You are the main customer service and store management assistant for our online store.
        Your job is to understand the user's intent and invoke the appropriate tool:
        1. For product catalog, search, stock, or price questions -> call get_products.
        2. For order tracking, order status, or order inquiries -> call get_order_status.
        3. For drafting or updating product descriptions -> call update_product_description.
        4. For nonsense, ambiguous, or unclassifiable inputs -> ask a polite clarifying question. Do NOT invoke tools for gibberish.
        Always provide clear, helpful answers based on tool results.""",
        model=model,
        tools=[catalog_tool, order_tool, copywriter_tool]
    )
    return agent


def run_agent_query(query: str) -> str:
    """Executes a natural language query through the Router Agent using ADK & LiteLlm."""
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
        
        final_answer = ""
        for event in reversed(events):
            if hasattr(event, "content") and event.content and event.content.role == "model":
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_answer = part.text
                        break
                if final_answer:
                    break
        
        return final_answer if final_answer else "I'm sorry, I couldn't process your request."
            
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ADK LLM execution fallback due to: {e}")
        return f"Error executing query: {e!s}"

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "Where is order 12?"
    print(run_agent_query(q))
