# Commerce Agent (Google ADK Python + LiteLLM / Ollama)

AI Agent built with **Google ADK (Agent Development Kit)** and **LiteLLM** for catalog search and product Q&A against live store data from PrestaShop.

## Architecture

- **Framework**: Google ADK (`Agent`, `Runner`, `InMemorySessionService`)
- **LLM Backend**: `google.adk.models.lite_llm.LiteLlm` wrapping local Ollama models (`olmo-3.1:32b-instruct`).
- **Tool**: `get_products(query: str)` using `PrestaShopClient` to query live store products and stock quantities via HTTP Basic Auth.
- **Resilience**: Lazy configuration loading ensures unit tests run cleanly without `.env`.

---

## Quickstart

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Sync dependencies
uv sync

# 3. Run ruff linter
uv run ruff check .

# 4. Run unit tests (no .env required)
uv run pytest -m "not integration"

# 5. Run integration tests against live PrestaShop container
uv run pytest

# 6. Execute catalog Q&A CLI query via Google ADK
uv run python -m commerce_agent "Do we have any Electronics? What do they cost?"
```

---

## 📸 Real & Reproducible Terminal Transcript

The transcript below is generated from an actual run against the live seeded PrestaShop store:

```text
$ uv run python -m commerce_agent "Do we have any Electronics? What do they cost?"

Question: Do we have any Electronics? What do they cost?

Agent Answer:
Yes, we have many Electronics products available. Here are some examples with their exact prices and stock quantities:

- Electronics Product 1 (ID: 20): $67.63, Stock: 100
- Electronics Product 2 (ID: 21): $442.72, Stock: 100
- Electronics Product 3 (ID: 22): $464.06, Stock: 100
- Electronics Product 4 (ID: 23): $153.03, Stock: 100
- Electronics Product 5 (ID: 24): $52.72, Stock: 100
- ...and many more with prices ranging from $11.76 to $479.16, all currently in stock at 100 units each.

If you want details about a specific product or a narrower search, please let me know!
```
