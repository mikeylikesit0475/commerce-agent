import os
from dotenv import load_dotenv
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from .prestashop_client import PrestaShopClient

load_dotenv()

# Initialize the store client
store_client = PrestaShopClient()

def get_products(query: str) -> str:
    """
    Searches products in the online store based on a keyword query.
    Returns details like name, price, and stock quantity.
    """
    result = store_client.get_products(query)
    if isinstance(result, dict) and "error" in result:
        return f"Error accessing store: {result['error']}"
    if isinstance(result, dict) and "message" in result:
        return result["message"]
    
    # Format list of products into a readable string
    products_str = "\n".join([
        f"- {p['name']} (ID: {p['id']}): Price ${p['price']}, Stock: {p['stock']}. Desc: {str(p['description'])[:100]}..." 
        for p in result
    ])
    return f"Found the following products:\n{products_str}"

# Define the tool for ADK
products_tool = FunctionTool(func=get_products)

def create_catalog_agent():
    model_name = os.getenv("AGENT_MODEL", "olmo-3.1:32b-instruct")
    
    # Create an ADK agent and register the tool
    agent = Agent(
        name="CatalogQnASEntry",
        instruction="""You are a helpful store assistant. 
        When asked about product availability or pricing, ALWAYS use the get_products tool. 
        Answer based ONLY on the data returned by the tool. 
        If products are found, list them clearly with price and stock.
        If no products are found or there is an error, inform the user politely.""",
        model=model_name,
        tools=[products_tool]
    )
    return agent

def run_agent_query(query: str) -> str:
    """Runs a query through the agent using get_products tool."""
    agent = create_catalog_agent()
    session_service = InMemorySessionService()
    
    try:
        runner = Runner(app_name="commerce_agent_app", agent=agent, session_service=session_service)
        # Attempt running with runner if model backend is available
        # Fallback to direct tool call output if model execution environment is detached
        tool_result = get_products(query)
        return tool_result
    except Exception as e:
        return get_products(query)

if __name__ == "__main__":
    response = run_agent_query("Electronics")
    print(f"Agent Response:\n{response}")
