"""
Optim COD Verification Agent
Automated logistics verification agent for Cash-on-Delivery orders.
"""

import json
import os
from openai import OpenAI

api_key = os.environ.get("GROK_API_KEY")
if not api_key:
    raise ValueError("GROK_API_KEY environment variable is not set")

client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

# ── Tool definition ────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "verify_order",
            "description": (
                "Finalises a COD order. Call this exactly once when the user has "
                "confirmed or cancelled the order and the address is resolved."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "is_confirmed": {
                        "type": "boolean",
                        "description": "True if the customer wants the order; False if cancelled.",
                    },
                    "updated_address": {
                        "type": ["string", "null"],
                        "description": (
                            "New address provided by the customer, or null if the "
                            "original address is correct / order is cancelled."
                        ),
                    },
                },
                "required": ["is_confirmed", "updated_address"],
            },
        }
    }
]

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
ROLE AND PERSONA
You are an automated logistics verification agent for the e-commerce brand Optim.
Your tone is professional, extremely concise, and helpful.
You are speaking on a phone call, so your responses must be SHORT — never longer
than one or two sentences. Do not use emojis, markdown, or lists.

OBJECTIVE
Verify a Cash-on-Delivery (COD) order for a premium tumbler and confirm the
shipping address before the warehouse dispatches it.

RULES OF ENGAGEMENT
1. STRICT CONSTRAINT: Do not answer questions about general store policies,
   refund policies, or product details. If the user asks something unrelated,
   reply exactly: "I am an automated dispatch assistant and only handle order
   verification. Please contact our support email for that."
2. NO HALLUCINATION: Do not promise delivery dates.
3. TOOL EXECUTION: You MUST call the verify_order tool exactly once — immediately
   after you have the customer's final decision and the address is resolved.

CONVERSATIONAL STATE MACHINE (follow strictly in order)

STATE 1 — GREETING
Say exactly:
"Hi, this is the automated dispatch system for Optim. We received a Cash-on-Delivery order for your recent tumbler purchase. Are you still interested in receiving this order?"

  * If user says NO  -> acknowledge, call verify_order(is_confirmed=false, updated_address=null), then go to STATE 3.
  * If user says YES -> go to STATE 2.

STATE 2 — ADDRESS VERIFICATION
Say exactly:
"Great. I have your shipping address as 123 Main Street. Is that correct, or do you need to update it?"

  * If address is CORRECT     -> call verify_order(is_confirmed=true, updated_address=null).
  * If user gives NEW address -> acknowledge it, then call verify_order(is_confirmed=true, updated_address=<new address>).
  After the tool call -> go to STATE 3.

STATE 3 — CALL TERMINATION
Say exactly:
"Perfect, your order has been updated in our system and will be dispatched shortly. Thank you."
Then stop — do not say anything further.
""".strip()


# ── Tool execution (mock) ──────────────────────────────────────────────────────

def verify_order(is_confirmed: bool, updated_address) -> dict:
    """Mock warehouse / OMS API call."""
    result = {
        "success": True,
        "is_confirmed": is_confirmed,
        "updated_address": updated_address,
        "message": (
            "Order confirmed and queued for dispatch."
            if is_confirmed
            else "Order cancelled successfully."
        ),
    }
    with open("order_log.json", "w") as f:
        json.dump(result, f, indent=2)
    return result


def execute_tool(name: str, inputs: dict) -> str:
    if name == "verify_order":
        result = verify_order(**inputs)
        return json.dumps(result)
    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Agentic conversation loop ──────────────────────────────────────────────────

def run_agent():
    print("\n" + "=" * 60)
    print("  OPTIM — COD Verification Agent")
    print("  (type 'quit' to exit at any time)")
    print("=" * 60 + "\n")

    messages = []

    def call_api():
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
        return client.chat.completions.create(
            model="grok-beta",
            max_tokens=512,
            tools=TOOLS,
            messages=msgs,
        )

    def extract_text(response) -> str:
        return response.choices[0].message.content or ""

    def get_tool_uses(response):
        if response.choices[0].message.tool_calls:
            return response.choices[0].message.tool_calls
        return []

    # Seed: ask the agent to open the call
    messages.append({"role": "user", "content": "Begin the verification call now."})
    response = call_api()
    messages.append({"role": "assistant", "content": response.choices[0].message.content})

    text = extract_text(response)
    if text:
        print(f"Agent : {text}\n")

    # Main loop
    while True:
        tool_uses = get_tool_uses(response)

        # ── Handle tool calls ──────────────────────────────────────────────
        if tool_uses:
            tool_results = []
            for tu in tool_uses:
                print(f"[TOOL] verify_order({tu.function.arguments})")
                # Parse the arguments from the function call
                import json as json_module
                args = json_module.loads(tu.function.arguments)
                result_str = execute_tool(tu.function.name, args)
                result_json = json_module.loads(result_str)
                print(f"[TOOL] -> {result_json['message']}\n")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_str,
                })

            messages.append({"role": "assistant", "content": response.choices[0].message.content})
            messages.append({"role": "user", "content": tool_results})
            response = call_api()
            messages.append({"role": "assistant", "content": response.choices[0].message.content})

            closing = extract_text(response)
            if closing:
                print(f"Agent : {closing}\n")

            print("=" * 60)
            print("  Call complete. See order_log.json for the record.")
            print("=" * 60 + "\n")
            break

        # ── Normal turn: get user input ────────────────────────────────────
        if response.choices[0].finish_reason == "stop" and not tool_uses:
            # Agent finished without a tool call — keep conversation going
            pass

        user_input = input("You   : ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("\nSession terminated.\n")
            break

        messages.append({"role": "user", "content": user_input})
        response = call_api()
        messages.append({"role": "assistant", "content": response.choices[0].message.content})

        text = extract_text(response)
        if text:
            print(f"\nAgent : {text}\n")


if __name__ == "__main__":
    run_agent()
