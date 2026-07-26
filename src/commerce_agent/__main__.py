import sys
from .agent import run_agent_query

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m commerce_agent \"Your question here\"")
        sys.exit(1)

    query = sys.argv[1]
    print(f"\nQuestion: {query}")
    response = run_agent_query(query)
    print(f"Agent Answer:\n{response}\n")

if __name__ == "__main__":
    main()
