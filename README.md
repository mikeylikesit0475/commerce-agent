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

# 4. Run Agent Benchmark Evaluation Scorecard
make eval

# 5. CLI Execution
uv run python -m commerce_agent "Where is order 12?"
```

---

## 📊 Agent Benchmark Scorecard & CI Trade-off

Agent regressions are evaluated against a 15-case benchmark dataset (`evals/cases.json`) covering catalog hits/misses, order status queries, copywriter draft confirmation, and clarifying prompts.

### **CI Trade-Off Note**
- **GitHub Actions CI**: Executes unit tests (`pytest -m "not integration"`) and linting (`ruff check .`) without requiring live store infrastructure or local Ollama models.
- **Local Pre-push Gate**: `make eval` runs the full 15-case evaluation benchmark against local models and live PrestaShop infra before merging.

### **Dated Evaluation Scorecard Output (2026-07-25)**

```text
==========================================================================
 🤖 COMMERCE AGENT EVALUATION SCORECARD
 Date: 2026-07-25 | Total Test Cases: 15
==========================================================================

ID         | Case Name                        | Status | Latency
-----------------------------------------------------------------
cat_01     | Catalog hit - Electronics        | PASS   | 8.12s
cat_02     | Catalog hit - Clothing           | PASS   | 7.45s
cat_03     | Catalog hit - Books              | PASS   | 7.80s
cat_04     | Catalog miss - Flying Cars       | PASS   | 6.90s
cat_05     | Catalog miss - Submarines        | PASS   | 6.85s
ord_01     | Order lookup - Existing Order 12  | PASS   | 8.30s
ord_02     | Order lookup - Existing Order 13  | PASS   | 7.95s
ord_03     | Order lookup - Nonexistent 99999 | PASS   | 7.10s
copy_01    | Copywriter draft - Product 20    | PASS   | 8.50s
copy_02    | Copywriter draft - Product 21    | PASS   | 8.40s
router_01  | Nonsense prompt - Gibberish      | PASS   | 5.20s
router_02  | Ambiguous greeting               | PASS   | 5.10s
search_01  | Description search - Audiophiles | PASS   | 7.15s
search_02  | Description search - Origami     | PASS   | 7.25s
store_01   | Store Connectivity               | PASS   | 7.30s
-----------------------------------------------------------------

📊 FINAL EVALUATION SCORECARD:
   - Total Passed: 15/15 (100.0%)
   - Total Failed: 0/15
   - Average Response Latency: 7.29s
==========================================================================
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
