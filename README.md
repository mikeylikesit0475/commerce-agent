# Commerce Router Agent (Google ADK + LiteLLM + Ollama)

An autonomous e-commerce AI assistant built on the **Google Agent Development Kit (ADK)** framework. Uses LiteLLM to interface with a locally hosted Ollama LLM (`olmo-3.1:32b-instruct`) and orchestrates tools across PrestaShop store APIs and the Commerce Core API.

---

## 🏗️ Architecture & Component Design

```
                     ┌───────────────────────────────┐
                     │   User Terminal / CLI REPL    │
                     └───────────────┬───────────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │     CommerceRouterAgent       │
                     │    (Google ADK + LiteLLM)     │
                     └───────────────┬───────────────┘
                                     │
         ┌───────────────────┬───────┴───────┬───────────────────┐
         │                   │               │                   │
         ▼                   ▼               ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  get_products   │ │get_order_status │ │update_product_  │ │  get_inventory_ │
│                 │ │                 │ │   description   │ │     alerts      │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │                   │
         ▼                   ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐ ┌─────────────────┐
│               PrestaShop Webservice API                 │ │Commerce Core API│
│                 (http://localhost:8080)                 │ │ (localhost:5275)│
└─────────────────────────────────────────────────────────┘ └─────────────────┘
```

### **Specialist Tools**

1. **`get_products(query)`**: Queries PrestaShop catalog JSON endpoints and combines with stock availability data (`ps_stock_available`).
2. **`get_order_status(order_id)`**: Fetches order reference, payment status, total amount paid, and item details.
3. **`update_product_description(product_id, new_description, confirmed)`**:
   - **Draft Mode (`confirmed=False`)**: Presents formatted proposed description draft for review.
   - **Publish Mode (`confirmed=True`)**: Strips read-only XML fields and PUTs update to PrestaShop Webservice API.
4. **`get_inventory_alerts()`**: Authenticates against `commerce-core-api` using `SERVICE_TOKEN` and fetches active low-stock inventory alerts.

---

## 🔒 Deterministic Confirmation Flow Design

To ensure **safety and strict human oversight** over mutating store data:
1. **Model Draft Generation**: The LLM uses `update_product_description(confirmed=False)` to generate and propose description drafts.
2. **Deterministic CLI REPL**: Application logic in `commerce_agent.__main__` captures the draft state.
3. **Explicit User Approval**: The application code requires explicit user input (`yes`/`y`/`confirm`/`publish`) in the terminal. When confirmed, the application invokes the write path directly without depending on secondary model turns.

---

## 🤖 Model Rationale & Environment Configuration

- **Framework**: Built natively on **Google ADK** (`google.adk.Agent`, `google.adk.Runner`, `google.adk.tools.FunctionTool`).
- **Model**: `olmo-3.1:32b-instruct` running locally via Ollama.
- **Provider Adapter**: `google.adk.models.lite_llm.LiteLlm` (`ollama_chat/olmo-3.1:32b-instruct`).

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
CommerceAgent> Draft an updated description for product 20 as: High performance premium gadget.

Agent Answer:
[DRAFT DESCRIPTION FOR REVIEW]
Product: Electronics Product 1 (ID: 20)
Proposed New Description:
"High performance premium gadget."

Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)

CommerceAgent> yes

[CONFIRM RECEIVED] Publishing update to PrestaShop for Product #20...
[PRESTASHOP STORE UPDATED SUCCESSFULLY]
Product: Electronics Product 1 (ID: 20)
Stored Description in Database:
"High performance premium gadget."
```

### 2. Run Single Command Line Query

```bash
uv run python -m commerce_agent "Do we have any Electronics? What do they cost?"
```

---

## 🧪 Verification & Benchmark Scorecard

```bash
# Run pytest unit and integration tests
uv run pytest

# Run 15-case benchmark evaluation suite
uv run python evals/run_evals.py
```

### 📊 Real Live Benchmark Scorecard Results

```text
==========================================================================
 🤖 COMMERCE AGENT EVALUATION SCORECARD
 Date: 2026-07-26 | Total Test Cases: 15
==========================================================================

ID         | Case Name                        | Status | Latency
-----------------------------------------------------------------
cat_01     | Catalog hit - Electronics        | PASS   | 23.02s
cat_02     | Catalog hit - Clothing           | PASS   | 18.53s
cat_03     | Catalog hit - Books              | PASS   | 27.25s
cat_04     | Catalog miss - Flying Cars       | PASS   | 8.46s
cat_05     | Catalog miss - Submarines        | PASS   | 12.00s
ord_01     | Order lookup - Existing Order 6  | PASS   | 14.40s
ord_02     | Order lookup - Existing Order 7  | PASS   | 14.44s
ord_03     | Order lookup - Nonexistent Order | PASS   | 10.34s
copy_01    | Copywriter draft - Product 20    | PASS   | 13.78s
copy_02    | Copywriter draft - Product 21    | PASS   | 10.67s
router_01  | Nonsense prompt - Gibberish      | PASS   | 7.26s
router_02  | Ambiguous greeting               | PASS   | 10.75s
alert_01   | Inventory alerts lookup          | PASS   | 36.87s
store_01   | Sports & Outdoors search         | PASS   | 35.75s
store_down | Store Offline Handling           | PASS   | 28.02s
-----------------------------------------------------------------

📊 FINAL EVALUATION SCORECARD:
   - Total Passed: 15/15 (100.0%)
   - Total Failed: 0/15
   - Average Response Latency: 18.10s
==========================================================================
```
