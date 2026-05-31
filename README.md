# Optim COD Verification Agent

An automated phone-style verification agent for Optim's Cash-on-Delivery orders,
built with the OpenAI Python SDK and an agentic tool-use loop.

---

## How It Works

The agent follows a strict **3-state conversational state machine**:

```
STATE 1: Greeting  →  STATE 2: Address Verification  →  STATE 3: Termination
```

When the customer's decision and address are resolved, the agent fires the
`verify_order` tool (which calls your warehouse/OMS API) and closes the call.

---

## Project Structure

```
optim_cod_agent/
├── agent.py          # Main agent — state machine + agentic loop
├── requirements.txt  # Python dependencies
├── README.md         # This file
└── order_log.json    # Written after each call (auto-created)
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Grok API key

```bash
export GROK_API_KEY="gsk_..."
```

### 3. Run the agent

```bash
python agent.py
```

---

## Example Session

```
============================================================
  OPTIM — COD Verification Agent
  (type 'quit' to exit at any time)
============================================================

Agent : Hi, this is the automated dispatch system for Optim. We received a
        Cash-on-Delivery order for your recent tumbler purchase. Are you still
        interested in receiving this order?

You   : Yes

Agent : Great. I have your shipping address as 123 Main Street. Is that correct,
        or do you need to update it?

You   : Please update it to 456 Park Avenue, Mumbai 400001

Agent : Understood, I've noted your new address as 456 Park Avenue, Mumbai 400001.

[TOOL] verify_order({'is_confirmed': True, 'updated_address': '456 Park Avenue, Mumbai 400001'})
[TOOL] -> Order confirmed and queued for dispatch.

Agent : Perfect, your order has been updated in our system and will be dispatched
        shortly. Thank you.

============================================================
  Call complete. See order_log.json for the record.
============================================================
```

---

## Customising

| What to change | Where |
|---|---|
| Original shipping address | `SYSTEM_PROMPT` — change `123 Main Street` |
| Model | `call_api()` — change `model=` |
| Real OMS/warehouse API | `verify_order()` function in `agent.py` |
| Max response tokens | `max_tokens=` in `call_api()` |

---

## Out-of-Scope Queries

The agent will not answer policy, refund, or product questions:

```
You   : What is your return policy?
Agent : I am an automated dispatch assistant and only handle order verification.
        Please contact our support email for that.
```
