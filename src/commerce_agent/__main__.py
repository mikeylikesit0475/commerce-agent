import re
import sys

from commerce_agent.agent import generate_description_copy, run_agent_query
from commerce_agent.prestashop_client import PrestaShopClient


def interactive_repl():
    print("==================================================")
    print(" Commerce Agent Interactive CLI / REPL")
    print(" Explicit Commands: 'improve <product_id>' (e.g. 'improve 20')")
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

        # 1. Handle pending draft confirm or decline flow
        if pending_draft:
            if user_input.lower() in ("yes", "y", "confirm", "publish"):
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
            elif user_input.lower() in ("no", "n", "decline", "cancel"):
                print("[DRAFT DECLINED] Product description update cancelled.\n")
                pending_draft = None
                continue
            else:
                print("[DRAFT CANCELLED] Proceeding with new query...\n")
                pending_draft = None

        # 2. Handle explicit 'improve <product_id>' command (Architect Decision)
        match_improve = re.match(r"^improve\s+(\d+)$", user_input, re.IGNORECASE)
        if match_improve:
            prod_id = int(match_improve.group(1))
            print(f"\n[FETCHING PRODUCT #{prod_id} FROM PRESTASHOP...]")
            prod = client.get_product_by_id(prod_id)
            if "error" in prod:
                print(f"Error fetching product #{prod_id}: {prod['error']}\n")
                continue
            if "message" in prod:
                print(f"{prod['message']}\n")
                continue

            prod_name = prod.get("name", f"Product #{prod_id}")
            current_desc = prod.get("description", "")
            print(f"Product: {prod_name} (ID: {prod_id})")
            print(f"Current Description: \"{current_desc}\"")
            print("\n[GENERATING IMPROVED DESCRIPTION VIA LLM...]")

            new_copy = generate_description_copy(prod_name, current_desc)

            print("\nAgent Answer:")
            print("[DRAFT DESCRIPTION FOR REVIEW]")
            print(f"Product: {prod_name} (ID: {prod_id})")
            print("Proposed New Description:")
            print(f"\"{new_copy}\"\n")
            print("Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)\n")

            pending_draft = (prod_id, new_copy)
            continue

        # 3. Default: Run query through Router Agent
        response = run_agent_query(user_input)
        print(f"\nAgent Answer:\n{response}\n")


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
