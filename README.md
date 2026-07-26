# Commerce Router Agent (Google ADK + LiteLLM + Ollama)

An autonomous e-commerce AI assistant built on the **Google Agent Development Kit (ADK)** framework. Uses LiteLLM to interface with a locally hosted Ollama LLM (`olmo-3.1:32b-instruct`) and orchestrates specialist tools across PrestaShop store APIs and the Commerce Core API.

---

## 🏗️ Architecture & Component Design

```
                     ┌───────────────────────────────┐
                     │   User Terminal / CLI REPL    │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │     CommerceRouterAgent       │
                     │    (Google ADK + LiteLLM)     │
                     └───────────────┬───────────────┘
                                     │
         ┌───────────────────┼───────┴───────────────────┐
         │                   │                           │
         ▼                   ▼                           ▼
┌─────────────────┐ ┌─────────────────┐         ┌─────────────────┐
│  get_products   │ │get_order_status │         │  get_inventory_ │
│                 │ │                 │         │     alerts      │
└────────┬────────┘ └────────┬────────┘         └────────┬────────┘
         │                   │                           │
         ▼                   ▼                           ▼
┌─────────────────────────────────────────┐     ┌─────────────────┐
│        PrestaShop Webservice API        │     │Commerce Core API│
│         (http://localhost:8080)         │     │ (localhost:5275)│
└─────────────────────────────────────────┘     └─────────────────┘
```

### **Specialist Tools**

1. **`get_products(query)`**: Queries PrestaShop catalog JSON endpoints and combines with stock availability data (`ps_stock_available`).
2. **`get_order_status(order_id)`**: Fetches order reference, payment status, total amount paid, and item details.
3. **`get_inventory_alerts()`**: Authenticates against `commerce-core-api` using `SERVICE_TOKEN` and fetches active low-stock inventory alerts.

---

## 💡 Architectural Design Decision: "LLM Generates, Code Orchestrates"

Per architectural review findings, local models (such as `olmo-3.1:32b-instruct`) may experience capability ceilings when emitting structured tool-call events for complex write-path entry triggers.
To guarantee **100% reliability, safety, and strict human control**:
1. **Deterministic Workflow Entry**: The copywriter workflow entry is triggered via explicit CLI REPL command (`improve <product_id>`).
2. **LLM Generation**: Application code fetches product data and invokes the LLM for plain text copy generation only (no tool calling).
3. **Human Review & Deterministic Side Effect**: Application code displays `[DRAFT DESCRIPTION FOR REVIEW]` and executes the live PrestaShop API PUT update only upon explicit user confirmation (`yes`/`y`/`confirm`/`publish`).

---

## 🤖 Model Rationale & Environment Configuration

- **Framework**: Built natively on **Google ADK** (`google.adk.Agent`, `google.adk.Runner`, `google.adk.tools.FunctionTool`).
- **Model**: `olmo-3.1:32b-instruct` running locally via Ollama.
- **Provider Adapter**: `google.adk.models.lite_llm.LiteLlm` (`ollama_chat/olmo-3.1:32b-instruct`).
- **SERVICE_TOKEN Minting**: In development environments, mint a service JWT via `curl -s "http://localhost:5275/dev/token?role=service"` and set `SERVICE_TOKEN` in `.env`.

### Environment Variables (`.env`)

```env
PS_URL=http://localhost:8080/api
WEBSERVICE_KEY=your_random_32_char_key_here
AGENT_MODEL=olmo-3.1:32b-instruct
CORE_API_URL=http://localhost:5275
SERVICE_TOKEN=your_service_jwt_token_here
```

---

## 🚀 Quickstart & Usage

### 1. Run Interactive CLI / REPL Session

```bash
uv run python -m commerce_agent
```

Example Interactive Flow:
```text
CommerceAgent> improve 20

[FETCHING PRODUCT #20 FROM PRESTASHOP...]
Product: Electronics Product 1 (ID: 20)
Current Description: "Electronics Product 1 description"

[GENERATING IMPROVED DESCRIPTION VIA LLM...]

Agent Answer:
[DRAFT DESCRIPTION FOR REVIEW]
Product: Electronics Product 1 (ID: 20)
Proposed New Description:
"High performance Electronics Product 1 featuring premium quality craftsmanship, modern design, and durable reliability."

Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)

CommerceAgent> yes

[CONFIRM RECEIVED] Publishing update to PrestaShop for Product #20...
[PRESTASHOP STORE UPDATED SUCCESSFULLY]
Product: Electronics Product 1 (ID: 20)
Stored Description in Database:
"High performance Electronics Product 1 featuring premium quality craftsmanship, modern design, and durable reliability."
```

---

## 🧪 Verification & Benchmark Scorecard

```bash
# Run pytest unit and integration tests
uv run pytest

# Run 15-case benchmark evaluation suite (asserts expected_tool from ADK event trace)
uv run python evals/run_evals.py
```

### 📊 Automated Scorecard Output

<!-- EVAL:BEGIN -->
```text
==========================================================================
 🤖 COMMERCE AGENT EVALUATION SCORECARD
 Date: 2026-07-25 | Total Test Cases: 15
==========================================================================

ID         | Case Name                        | Status | Latency 
-----------------------------------------------------------------
cat_01     | Catalog hit - Electronics        | PASS   | 19.67s
cat_02     | Catalog hit - Clothing           | PASS   | 15.12s
cat_03     | Catalog hit - Books              | PASS   | 21.36s
cat_04     | Catalog miss - Flying Cars       | PASS   | 9.30s
cat_05     | Catalog miss - Submarines        | PASS   | 8.07s
cat_06     | Catalog hit - Home & Garden      | PASS   | 24.24s
cat_07     | Catalog hit - Sports & Outdoors  | PASS   | 24.72s
ord_01     | Order lookup - Existing Order 9  | PASS   | 12.60s
ord_02     | Order lookup - Existing Order 10 | FAIL   | 9.54s
ord_03     | Order lookup - Nonexistent Order | PASS   | 9.80s
router_01  | Nonsense prompt - Gibberish      | PASS   | 7.08s
router_02  | Ambiguous greeting               | PASS   | 7.76s
alert_01   | Inventory alerts lookup          | PASS   | 7.11s
store_01   | Specific product search - Sports | FAIL   | 10.33s
store_02   | Specific product search - Clothi | FAIL   | 9.53s
-----------------------------------------------------------------

📊 FINAL EVALUATION SCORECARD:
   - Total Passed: 12/15 (80.0%)
   - Total Failed: 3/15
   - Average Response Latency: 13.08s
==========================================================================
```
<!-- EVAL:END -->
