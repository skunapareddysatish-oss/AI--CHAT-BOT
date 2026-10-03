import re

from app.tools import AVAILABLE_FUNCTIONS
from app.memory import add_message, get_history
from app.rag import retrieve_context
from app.config import client, CHAT_MODEL


def chat_agent(session_id: str, user_message: str):
    """
    Main AI Agent.
    Decides whether to use a tool or Gemini + RAG.
    """

    add_message(session_id, "user", user_message)

    lower = user_message.lower()

    # -----------------------------
    # Tool Routing
    # -----------------------------

    if "time" in lower:
        reply = AVAILABLE_FUNCTIONS["time"]()

    elif "date" in lower or "today" in lower:
        reply = AVAILABLE_FUNCTIONS["date"]()

    elif lower.startswith("calculate"):

        expression = user_message[len("calculate"):].strip()

        reply = AVAILABLE_FUNCTIONS["calculator"](expression)

    elif "order" in lower:

        match = re.search(r"\d+", user_message)

        if match:

            result = AVAILABLE_FUNCTIONS["get_order_status"](match.group())

            reply = (
                f"Order ID: {result['order_id']}\n"
                f"Status: {result['status']}"
            )

        else:
            reply = "Please provide an Order ID."

    else:

        history = get_history(session_id)

        context = retrieve_context(user_message)

        history_text = ""

        for role, message in history:
            history_text += f"{role}: {message}\n"

        prompt = f"""
You are an advanced AI assistant.

Answer using the retrieved context whenever possible.

If the answer is not present in the context,
use your own knowledge.

Retrieved Context:
{context}

Conversation History:
{history_text}

User:
{user_message}

Assistant:
"""

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=prompt
        )

        reply = response.text

    add_message(session_id, "assistant", reply)

    return reply