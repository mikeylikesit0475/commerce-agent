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
- **SERVICE_TOKEN Minting**: In development environments, mint a service JWT from the Commerce Core API dev endpoint. The endpoint returns JSON of the form `{"token": "<jwt>"}` — extract the `.token` field and set it as `SERVICE_TOKEN` in `.env`:

  ```bash
  curl -s "http://localhost:5275/dev/token?role=service" | jq -r .token
  ```

  **Note:** the minted token **expires after 1 hour**. If `get_inventory_alerts` starts returning `Core API returned status 401`, mint a fresh token and update `.env`.

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
==================================================
 Commerce Agent Interactive CLI / REPL
 Explicit Commands: 'improve <product_id>' (e.g. 'improve 20')
 Type 'exit' or 'quit' to terminate.
==================================================

CommerceAgent> improve 20

[FETCHING PRODUCT #20 FROM PRESTASHOP...]
Product: Electronics Product 1 (ID: 20)
Current Description: "Electronics Product 1 description"

[GENERATING IMPROVED DESCRIPTION VIA LLM...]
Deprecated. Please migrate to the async method.

Agent Answer:
[DRAFT DESCRIPTION FOR REVIEW]
Product: Electronics Product 1 (ID: 20)
Proposed New Description:
"Experience seamless performance and cutting-edge innovation with Electronics Product 1—designed to elevate your everyday tech experience."

Please confirm: Do you want to publish this update to PrestaShop? (Reply 'yes' or 'confirm' to proceed)

CommerceAgent> yes

[CONFIRM RECEIVED] Publishing update to PrestaShop for Product #20...
[PRESTASHOP STORE UPDATED SUCCESSFULLY]
Product: Electronics Product 1 (ID: 20)
Stored Description in Database:
"Experience seamless performance and cutting-edge innovation with Electronics Product 1—designed to elevate your everyday tech experience."

CommerceAgent> exit
Goodbye!
```

> **Known limitation — session continuity:** each REPL query runs in a fresh agent session (no conversational memory between turns); only the pending `improve <id>` draft awaiting confirmation spans turns.

---

## 🧪 Verification & Benchmark Scorecard

```bash
# Run pytest unit and integration tests
uv run pytest

# Run 16-case benchmark evaluation suite (asserts expected_tool from ADK event trace)
uv run python evals/run_evals.py
```

**Exception-suppression policy:** broad `except Exception` (`BLE001`) suppressions are not allowed in application code — every handler catches specific exception types; the single remaining `# noqa: BLE001` (the eval harness boundary in `evals/run_evals.py`) carries an inline one-line justification.

### 📊 Automated Scorecard Output

<!-- EVAL:BEGIN -->
```text
==========================================================================
 🤖 COMMERCE AGENT EVALUATION SCORECARD
 Date: 2026-07-25 | Total Test Cases: 16
==========================================================================

ID         | Case Name                        | Status | Latency 
-----------------------------------------------------------------
cat_01     | Catalog hit - Electronics        | FAIL   | 7.73s
cat_02     | Catalog hit - Clothing           | PASS   | 16.13s
cat_03     | Catalog hit - Books              | FAIL   | 8.59s
cat_04     | Catalog miss - Flying Cars       | PASS   | 8.33s
cat_05     | Catalog miss - Submarines        | PASS   | 7.92s
cat_06     | Catalog hit - Home & Garden      | PASS   | 25.68s
cat_07     | Catalog hit - Sports & Outdoors  | PASS   | 23.13s
ord_01     | Order lookup - Existing Order 12 | PASS   | 11.97s
ord_02     | Order lookup - Existing Order 13 | FAIL   | 9.73s
ord_03     | Order lookup - Nonexistent Order | PASS   | 6.60s
router_01  | Nonsense prompt - Gibberish      | PASS   | 6.26s
router_02  | Ambiguous greeting               | PASS   | 6.88s
alert_01   | Inventory alerts lookup          | PASS   | 6.30s
store_down | Store offline - error surfaced   | PASS   | 14.79s
store_01   | Specific product search - Sports | FAIL   | 11.19s
store_02   | Specific product search - Clothi | FAIL   | 9.36s
-----------------------------------------------------------------

📊 FINAL EVALUATION SCORECARD:
   - Total Passed: 11/16 (68.8%)
   - Total Failed: 5/16
   - Average Response Latency: 11.29s
==========================================================================
```
<!-- EVAL:END -->

**Reading the scorecard honestly:** the verified baseline with `olmo-3.1:32b-instruct` is 11/16. All five failures share one failure mode — the model sometimes declines to emit a tool call for certain phrasings and asks for a keyword instead (a known ceiling of local models on tool-calling; see the design decision above for why side effects and workflow entry don't depend on it). `make eval` enforces a **regression floor of 10** (catches real regressions without failing on single-case nondeterminism); the aspirational target is 12+, reachable by swapping `AGENT_MODEL` to a stronger tool-calling model.
