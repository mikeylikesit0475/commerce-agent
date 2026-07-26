import sys
from commerce_agent.agent import run_agent_query
from commerce_agent.prestashop_client import PrestaShopClient


def interactive_repl():
    print("==================================================")
    print(" Commerce Agent Interactive CLI / REPL")
    print(" Type 'exit' or 'quit' to terminate.")
    print("==================================================\n")

    client = PrestaShopClient()
    pending_draft = None  # tuple: (product_id, new_description)

    while True:
        try:
            user_input = input("CommerceAgent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        # Check for pending draft confirm flow
        if pending_draft and user_input.lower() in ("yes", "y", "confirm", "publish"):
            prod_id, new_desc = pending_draft
            print(f"\n[CONFIRM RECEIVED] Publishing update to PrestaShop for Product #{prod_id}...")
            res = client.update_product_description(prod_id, new_desc)
            if "error" in res:
                print(f"Error updating product: {res['error']}\n")
            else:
                verify_prod = client.get_product_by_id(prod_id)
                print("[PRESTASHOP STORE UPDATED SUCCESSFULLY]")
                print(f"Product: {verify_prod.get('name')} (ID: {prod_id})")
                print(f"Stored Description in Database:\n\"{verify_prod.get('description')}\"\n")
            pending_draft = None
            continue
        elif pending_draft:
            print("[DRAFT CANCELLED] Proceeding with new query...\n")
            pending_draft = None

        # Run query through Router Agent
        response, draft_info = run_agent_query_with_draft_info(user_input)
        print(f"\nAgent Answer:\n{response}\n")

        if draft_info:
            pending_draft = draft_info


def run_agent_query_with_draft_info(query: str):
    """Executes agent query and detects if a draft description for review was returned."""
    answer = run_agent_query(query)
    
    # Check if answer contains DRAFT info to extract pending_draft
    draft_info = None
    if "[DRAFT DESCRIPTION FOR REVIEW]" in answer:
        import re
        match_id = re.search(r"ID:\s*(\d+)", answer)
        match_desc = re.search(r'Proposed New Description:\s*"(.*?)"', answer, re.DOTALL)
        if match_id and match_desc:
            draft_info = (int(match_id.group(1)), match_desc.group(1).strip())
    
    return answer, draft_info


def main():
    if len(sys.argv) < 2:
        interactive_repl()
    else:
        query = " ".join(sys.argv[1:])
        print(f"\nQuestion: {query}")
        response = run_agent_query(query)
        print(f"Agent Answer:\n{response}\n")


if __name__ == "__main__":
    main()
