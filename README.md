# Commerce Agent (Google ADK Python)

AI Agent built with **Google ADK (Agent Development Kit)** for answering catalog questions against live store data from PrestaShop.

## Architecture

- **Framework**: Google ADK (Python)
- **Tool**: `get_products(query: str)` using `PrestaShopClient` to query live store products via HTTP Basic Auth.
- **Agent**: `CatalogQnASEntry` agent configured to search the store catalog and answer user queries using live data.
- **Model**: `AGENT_MODEL` (default: `olmo-3.1:32b-instruct` / local Ollama compatible model).

---

## Quickstart

```bash
# 1. Install dependencies
uv sync

# 2. Run catalog query CLI
uv run python -m commerce_agent "Do we have any Electronics? What do they cost?"

# 3. Run unit tests
uv run pytest -m "not integration"

# 4. Run integration test (requires platform-infra PrestaShop container)
uv run pytest
```

---

## Real Q&A Transcript

```text
$ uv run python -m commerce_agent "Electronics"

Question: Electronics
Agent Answer:
Found the following products:
- Electronics Product 1 (ID: 152): Price $348.27, Stock: 0. Desc: Electronics Product 1 short description...
- Electronics Product 2 (ID: 153): Price $479.16, Stock: 0. Desc: Electronics Product 2 short description...
- Electronics Product 3 (ID: 154): Price $188.19, Stock: 0. Desc: Electronics Product 3 short description...
- Electronics Product 4 (ID: 155): Price $75.12, Stock: 0. Desc: Electronics Product 4 short description...
- Electronics Product 5 (ID: 156): Price $208.14, Stock: 0. Desc: Electronics Product 5 short description...
- Electronics Product 6 (ID: 157): Price $345.91, Stock: 0. Desc: Electronics Product 6 short description...
```
