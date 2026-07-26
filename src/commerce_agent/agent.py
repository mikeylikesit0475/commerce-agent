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

def get_products(query: str) -> str:
    """
    Searches products in the PrestaShop store by keyword query (matches name or description).
    Returns a formatted string listing matching products with their price, stock quantity, and description.
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

# Wrap function in ADK FunctionTool
products_tool = FunctionTool(func=get_products)

def create_catalog_agent():
    raw_model_name = os.getenv("AGENT_MODEL", "olmo-3.1:32b-instruct")
    
    # Ensure model uses ollama_chat prefix for LiteLlm wrapper
    if not raw_model_name.startswith("ollama_chat/") and not raw_model_name.startswith("ollama/"):
        model_spec = f"ollama_chat/{raw_model_name}"
    else:
        model_spec = raw_model_name

    model = LiteLlm(model=model_spec)
    
    agent = Agent(
        name="CatalogQnASEntry",
        instruction="""You are a store assistant. 
        When asked about product availability, prices, or store inventory, ALWAYS call the get_products tool. 
        Answer based ONLY on the data returned by the get_products tool. 
        List matching products clearly with exact price and stock quantity.
        If no products are found, inform the user politely.""",
        model=model,
        tools=[products_tool]
    )
    return agent

def run_agent_query(query: str) -> str:
    """Executes a natural language query through the ADK Agent & Runner with LiteLlm."""
    session_service = InMemorySessionService()
    
    try:
        agent = create_catalog_agent()
        runner = Runner(app_name="commerce_agent_app", agent=agent, session_service=session_service)
        session = session_service.create_session_sync(app_name="commerce_agent_app", user_id="user_cli")
        
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )
        
        events = list(runner.run(user_id="user_cli", session_id=session.id, new_message=message))
        
        # Extract the final model text output from the events
        final_answer = ""
        for event in reversed(events):
            if hasattr(event, "content") and event.content and event.content.role == "model":
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        final_answer = part.text
                        break
                if final_answer:
                    break
        
        if final_answer:
            return final_answer
        else:
            return get_products(query)
            
    except Exception as e:  # noqa: BLE001
        logger.warning(f"ADK LLM execution fallback due to: {e}")
        # Fallback cleanly if LLM model runner encounters environment issues
        return get_products(query)

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "Do we have any Electronics? What do they cost?"
    print(run_agent_query(q))
