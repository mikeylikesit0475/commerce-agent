# Commerce Agent (Multi-Agent System with Google ADK + LiteLLM)

Multi-agent AI platform built with **Google ADK** (`Agent`, `Runner`, `InMemorySessionService`) and **LiteLLM** wrapping local Ollama models (`olmo-3.1:32b-instruct`).

## 📐 Architecture Diagram

```text
                               +-----------------------------+
                               |     CommerceRouterAgent     |
                               |    (Intent Classifier)      |
                               +--------------+--------------+
                                              |
      +---------------------------------------+---------------------------------------+
      |                                       |                                       |
      v                                       v                                       v
+-----------------------+           +-----------------------+           +-----------------------+
|   CatalogSpecialist   |           | OrderSupportSpecialist|           |  CopywriterSpecialist |
+-----------+-----------+           +-----------+-----------+           +-----------+-----------+
            |                                   |                                   |
            v                                   v                                   v
    get_products()                      get_order_status()              update_product_description()
            |                                   |                                   |
            +-----------------------------------+-----------------------------------+
                                                |
                                                v
                               +-----------------------------+
                               |   PrestaShop Webservice API |
                               | (Products, Orders, Stock)   |
                               +-----------------------------+
```

### Design Rationale: Multi-Tool Router Agent
The router agent acts as a unified entry point, utilizing tool schemas and intent instructions to select the appropriate specialist tool. This avoids redundant round-trips while enforcing domain safety (e.g., draft confirmation before database mutation).

---

## 🚀 Quickstart

```bash
# 1. Environment & Dependencies
cp .env.example .env
uv sync

# 2. Linting & Unit Testing
uv run ruff check .
uv run pytest -m "not integration"

# 3. Integration Testing against PrestaShop
uv run pytest

# 4. CLI Execution
uv run python -m commerce_agent "Where is order 12?"
```

---

## 📸 Real & Reproducible Transcripts

### 1. Order Support Specialist ("Where is order 12?")
```text
$ uv run python -m commerce_agent "Where is order 12?"

Question: Where is order 12?
Agent Answer:
Order #12 has a status of "Payment accepted / Processing." The total paid is $348.27, and it was placed on July 25th, 2026 at 8:35 PM.
```

### 2. Catalog Specialist ("Do we have any Electronics?")
```text
$ uv run python -m commerce_agent "Do we have any Electronics? What do they cost?"

Question: Do we have any Electronics? What do they cost?
Agent Answer:
Yes, we have many Electronics products available. Here are some examples with their exact prices and stock quantities:

- Electronics Product 1 (ID: 20): $67.63, Stock: 100
- Electronics Product 2 (ID: 21): $442.72, Stock: 100
- Electronics Product 3 (ID: 22): $464.06, Stock: 100
- ...all currently in stock at 100 units each.
```

### 3. Copywriter Specialist (Draft Review Flow)
```text
$ uv run python -m commerce_agent "Improve description for product 20 to 'High performance premium flagship electronics gadget.'"

Question: Improve description for product 20 to 'High performance premium flagship electronics gadget.'
Agent Answer:
[DRAFT DESCRIPTION FOR REVIEW]
Product: Electronics Product 1 (ID: 20)
Proposed New Description:
"High performance premium flagship electronics gadget."

Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)
```

### 4. Nonsense / Ambiguous Prompt (Clarification Flow)
```text
$ uv run python -m commerce_agent "asdfghjk 12345"

Question: asdfghjk 12345
Agent Answer:
I'm sorry, I didn't understand your request. Could you please clarify what information or assistance you're looking for?
```
