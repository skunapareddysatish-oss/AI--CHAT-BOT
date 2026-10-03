import re
import time

try:
    from google.genai import types
    from google.genai import errors
except ImportError:  # pragma: no cover - deployment installs google-genai
    types = None
    errors = None

from app.tools import AVAILABLE_FUNCTIONS, TOOL_SCHEMAS
from app.memory import (
    add_message,
    get_history,
    create_conversation
)
from app.rag import retrieve_context
from app.config import client, CHAT_MODEL


# ============================================================
# GEMINI RETRY SETTINGS
# ============================================================

MAX_GEMINI_RETRIES = 3

RETRY_DELAYS = [
    2,
    5,
    10
]


# ============================================================
# WEATHER CITY EXTRACTION
# ============================================================

def extract_weather_city(message: str):
    """
    Extract a city name from a weather-related question.
    """

    text = message.lower().strip()

    # Remove punctuation
    text = re.sub(r"[?!.,]", "", text)

    patterns = [

        # CURRENT WEATHER
        r"what's the weather in (.+)",
        r"what is the weather in (.+)",
        r"what's weather in (.+)",
        r"what is weather in (.+)",
        r"how is the weather in (.+)",
        r"how's the weather in (.+)",
        r"weather in (.+)",
        r"weather of (.+)",

        # FORECAST
        r"what's the forecast for (.+)",
        r"what is the forecast for (.+)",
        r"what's the forecast in (.+)",
        r"what is the forecast in (.+)",
        r"give me the forecast for (.+)",
        r"give me the forecast in (.+)",
        r"give me weather for (.+)",
        r"give me weather in (.+)",
        r"weather forecast for (.+)",
        r"weather forecast in (.+)",
        r"forecast for (.+)",
        r"forecast in (.+)",

        # TEMPERATURE
        r"what's the temperature in (.+)",
        r"what is the temperature in (.+)",
        r"temperature in (.+)",
        r"temperature of (.+)",

        # RAIN
        r"will it rain in (.+)",
        r"will it rain tomorrow in (.+)",
        r"will it rain today in (.+)",
        r"is it going to rain in (.+)",
        r"is it going to rain tomorrow in (.+)",
        r"will there be rain in (.+)",
        r"will there be rain tomorrow in (.+)",

        # HEAT
        r"how hot is (.+)",
        r"how hot will (.+)",
    ]

    for pattern in patterns:

        match = re.search(pattern, text)

        if match:

            city = match.group(1).strip()

            # Remove time/follow-up words
            city = re.sub(
                r"\b(tomorrow|today|next 5 days|next five days)\b",
                "",
                city
            )

            city = re.sub(
                r"\s+",
                " ",
                city
            ).strip()

            if city:
                return city

    return ""


# ============================================================
# FIND PREVIOUS WEATHER CITY
# ============================================================

def get_previous_weather_city(session_id: str):
    """
    Find the latest city mentioned in a weather-related
    user message.
    """

    history = get_history(session_id)

    for role, message in reversed(history):

        if role != "user":
            continue

        message_lower = message.lower()

        if not any(
            word in message_lower
            for word in [
                "weather",
                "temperature",
                "forecast",
                "rain",
                "raining",
                "rainy",
                "hot"
            ]
        ):
            continue

        city = extract_weather_city(message)

        if city:
            return city

    return ""


# ============================================================
# BUILD HISTORY TEXT
# ============================================================

def build_history_text(session_id: str):
    """
    Convert stored conversation history into text.
    """

    history = get_history(session_id)

    history_text = ""

    for role, message in history:

        if role == "user":

            history_text += (
                f"User: {message}\n"
            )

        else:

            history_text += (
                f"Assistant: {message}\n"
            )

    return history_text


# ============================================================
# CREATE GEMINI TOOL
# ============================================================

def create_gemini_tool():
    """
    Convert TOOL_SCHEMAS into a Gemini Tool object.
    """

    function_declarations = []

    for tool in TOOL_SCHEMAS:

        declaration = types.FunctionDeclaration(
            name=tool["name"],
            description=tool["description"],
            parameters=tool["parameters"]
        )

        function_declarations.append(
            declaration
        )

    return types.Tool(
        function_declarations=function_declarations
    )


# ============================================================
# GEMINI REQUEST WITH RETRY
# ============================================================

def gemini_generate(
    contents,
    config
):
    """
    Send request to Gemini.

    Automatically retries temporary Gemini errors such as:

        503 UNAVAILABLE
        429 RESOURCE_EXHAUSTED
        500 SERVER ERROR

    using exponential backoff.
    """

    if client is None:
        return None

    last_error = None

    for attempt in range(MAX_GEMINI_RETRIES):

        try:

            print(
                f"\nGemini request attempt "
                f"{attempt + 1}/{MAX_GEMINI_RETRIES}"
            )

            response = client.models.generate_content(
                model=CHAT_MODEL,
                contents=contents,
                config=config
            )

            print("Gemini request successful.")

            return response

        except errors.ServerError as e:

            last_error = e

            print(
                "\nGemini temporary server error:"
            )

            print(e)

            if attempt < MAX_GEMINI_RETRIES - 1:

                delay = RETRY_DELAYS[attempt]

                print(
                    f"Retrying Gemini in "
                    f"{delay} seconds..."
                )

                time.sleep(delay)

            else:

                print(
                    "Gemini retry limit reached."
                )

        except errors.APIError as e:

            last_error = e

            print(
                "\nGemini API error:"
            )

            print(e)

            # Retry only server-side errors
            if getattr(e, "code", None) in [
                429,
                500,
                502,
                503,
                504
            ]:

                if attempt < MAX_GEMINI_RETRIES - 1:

                    delay = RETRY_DELAYS[attempt]

                    print(
                        f"Retrying Gemini in "
                        f"{delay} seconds..."
                    )

                    time.sleep(delay)

                    continue

            # Non-retryable error
            break

        except Exception as e:

            last_error = e

            print(
                "\nUnexpected Gemini error:"
            )

            print(e)

            break

    # --------------------------------------------------------
    # DO NOT CRASH FASTAPI
    # --------------------------------------------------------

    print(
        "\nGemini failed after all attempts."
    )

    print(
        f"Last error: {last_error}"
    )

    return None


# ============================================================
# GEMINI FUNCTION CALLING
# ============================================================

def run_gemini_with_tools(
    user_message: str,
    history_text: str
):
    """
    Complete Gemini function-calling workflow.

    1. Send request + tools to Gemini.
    2. Gemini chooses a function if necessary.
    3. Python executes that function.
    4. Send function result back to Gemini.
    5. Gemini generates final response.
    """

    if client is None or types is None:
        return (
            "Gemini is not configured on this deployment yet. "
            "Add GEMINI_API_KEY to enable the full AI assistant. "
            "I can still help with time, date, calculations, order status, "
            "and weather when their providers are configured."
        )

    prompt = f"""
You are an advanced AI assistant.

You have access to these tools:

- get_time
- get_date
- calculator
- get_order_status
- get_weather
- get_weather_forecast
- get_tomorrow_weather
- get_rain_prediction
- web_search
- wikipedia_search

Use tools when the user needs:

- current time
- today's date
- calculations
- order information
- current weather
- tomorrow's weather
- weather forecast
- rain prediction
- the user asks for current information
- the user asks for recent information
- the user asks to search the internet
- the user asks about latest news
- the answer may have changed since your training data
- the user explicitly says "search the web"
- the user asks about an encyclopedic topic
- the user asks about a person
- the user asks about a historical event
- the user asks about a scientific concept
- the user asks about a place
- Wikipedia would be a useful source

Use the conversation history to understand
follow-up questions.

For example:

User: What's the weather in Delhi?
Assistant: Weather information...

User: Will it rain?
The city is Delhi.

Retrieved Knowledge and Conversation:
{history_text}

User:
{user_message}
"""

    # --------------------------------------------------------
    # CREATE GEMINI TOOL
    # --------------------------------------------------------

    gemini_tool = create_gemini_tool()

    config = types.GenerateContentConfig(
        tools=[gemini_tool]
    )

    # --------------------------------------------------------
    # FIRST GEMINI REQUEST
    # --------------------------------------------------------

    response = gemini_generate(
        contents=prompt,
        config=config
    )

    # --------------------------------------------------------
    # GEMINI UNAVAILABLE
    # --------------------------------------------------------

    if response is None:

        return (
            "Gemini is temporarily unavailable because "
            "the Gemini service is experiencing high demand. "
            "Please try again in a few seconds."
        )

    # --------------------------------------------------------
    # CHECK FOR FUNCTION CALL
    # --------------------------------------------------------

    function_calls = getattr(response, "function_calls", None) or []

    # --------------------------------------------------------
    # NO TOOL REQUIRED
    # --------------------------------------------------------

    if not function_calls:

        if response.text:

            return response.text

        return (
            "Gemini returned an empty response."
        )

    # --------------------------------------------------------
    # EXECUTE FUNCTION CALLS
    # --------------------------------------------------------

    function_response_parts = []

    for function_call in function_calls:

        function_name = function_call.name

        function_args = dict(
            function_call.args or {}
        )

        print(
            f"\nGemini requested tool: "
            f"{function_name}"
        )

        print(
            f"Arguments: "
            f"{function_args}"
        )

        # ----------------------------------------------------
        # FIND PYTHON FUNCTION
        # ----------------------------------------------------

        function = AVAILABLE_FUNCTIONS.get(
            function_name
        )

        if function is None:

            tool_result = {
                "error":
                f"Unknown function: {function_name}"
            }

        else:

            try:

                # Execute Python function
                tool_result = function(
                    **function_args
                )

            except TypeError as e:

                tool_result = {
                    "error":
                    f"Invalid arguments for "
                    f"{function_name}: {str(e)}"
                }

            except Exception as e:

                tool_result = {
                    "error":
                    str(e)
                }

        print(
            f"Tool result: "
            f"{tool_result}"
        )

        # ----------------------------------------------------
        # CREATE GEMINI FUNCTION RESPONSE
        # ----------------------------------------------------

        function_response_parts.append(
    types.Part.from_function_response(
        name=function_name,
        response={
            "result": tool_result
        }
    )
)

    # --------------------------------------------------------
    # SEND TOOL RESULTS BACK TO GEMINI
    # --------------------------------------------------------

    if not getattr(response, "candidates", None):
        return "The tool completed, but Gemini did not return a usable response."

    final_contents = [

        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=prompt
                )
            ]
        ),

        response.candidates[0].content,

        types.Content(
            role="user",
            parts=function_response_parts
        )
    ]

    # --------------------------------------------------------
    # FINAL GEMINI REQUEST
    # --------------------------------------------------------

    final_response = gemini_generate(
        contents=final_contents,
        config=config
    )

    # --------------------------------------------------------
    # FINAL REQUEST FAILED
    # --------------------------------------------------------

    if final_response is None:

        return (
            "I successfully processed the requested tool, "
            "but Gemini is temporarily unavailable while "
            "generating the final response. "
            "Please try again."
        )

    # --------------------------------------------------------
    # RETURN FINAL RESPONSE
    # --------------------------------------------------------

    if final_response.text:

        return final_response.text

    return (
        "Gemini returned an empty final response."
    )


# ============================================================
# MAIN CHAT AGENT
# ============================================================

def chat_agent(
    session_id: str,
    user_message: str
):
    """
    Main chatbot agent.

    Supports:

    - Time
    - Date
    - Calculator
    - Order status
    - Current weather
    - Tomorrow weather
    - Rain prediction
    - 5-day forecast
    - Follow-up weather questions
    - Gemini
    - RAG
    - Gemini function calling
    """

    user_message = user_message.strip()

    if not user_message:

        return (
            "Please enter a message."
        )

    lower = user_message.lower()

    # Capture history before the current message is added.  The current
    # message is supplied separately to Gemini, which avoids duplicating it in
    # the prompt while preserving it for weather follow-ups.
    history_text = build_history_text(session_id)

    create_conversation(
        session_id
    )

    add_message(
        session_id,
        "user",
        user_message
    )

    reply = None

    # ========================================================
    # TIME
    # ========================================================

    if (
        "what time" in lower
        or "current time" in lower
        or lower == "time"
    ):

        reply = AVAILABLE_FUNCTIONS[
            "get_time"
        ]()

    # ========================================================
    # DATE
    # ========================================================

    elif (
        "today's date" in lower
        or "todays date" in lower
        or "what date" in lower
        or lower == "date"
    ):

        reply = AVAILABLE_FUNCTIONS[
            "get_date"
        ]()

    # ========================================================
    # CALCULATOR
    # ========================================================

    elif lower.startswith(
        "calculate"
    ):

        expression = user_message[
            len("calculate"):
        ].strip()

        if expression:

            reply = AVAILABLE_FUNCTIONS[
                "calculator"
            ](
                expression
            )

        else:

            reply = (
                "Please provide a mathematical "
                "expression."
            )

    # ========================================================
    # ORDER STATUS
    # ========================================================

    elif (
        "order" in lower
        and re.search(
            r"\d+",
            user_message
        )
    ):

        match = re.search(
            r"\d+",
            user_message
        )

        order_id = match.group()

        result = AVAILABLE_FUNCTIONS[
            "get_order_status"
        ](
            order_id
        )

        if result["status"] == "Not Found":

            reply = (
                f"Order {order_id} "
                f"was not found."
            )

        else:

            reply = (
                f"Order ID: "
                f"{result['order_id']}\n"
                f"Status: "
                f"{result['status']}"
            )

    # ========================================================
    # TOMORROW RAIN
    # ========================================================

    elif (
        "tomorrow" in lower
        and (
            "rain" in lower
            or "raining" in lower
            or "rainy" in lower
        )
    ):

        city = extract_weather_city(
            user_message
        )

        if not city:

            city = get_previous_weather_city(
                session_id
            )

        if city:

            reply = AVAILABLE_FUNCTIONS[
                "get_rain_prediction"
            ](
                city,
                tomorrow=True
            )

        else:

            reply = (
                "Please provide a city name."
            )

    # ========================================================
    # TOMORROW WEATHER
    # ========================================================

    elif (
        "tomorrow" in lower
        and (
            "weather" in lower
            or "temperature" in lower
            or "what about" in lower
            or "how about" in lower
        )
    ):

        city = extract_weather_city(
            user_message
        )

        if not city:

            city = get_previous_weather_city(
                session_id
            )

        if city:

            reply = AVAILABLE_FUNCTIONS[
                "get_tomorrow_weather"
            ](
                city
            )

        else:

            reply = (
                "Please provide a city name."
            )

    # ========================================================
    # GENERAL RAIN
    # ========================================================

    elif (
        "rain" in lower
        or "raining" in lower
        or "rainy" in lower
        or "precipitation" in lower
    ):

        city = extract_weather_city(
            user_message
        )

        if not city:

            city = get_previous_weather_city(
                session_id
            )

        if city:

            reply = AVAILABLE_FUNCTIONS[
                "get_rain_prediction"
            ](
                city
            )

        else:

            reply = (
                "Please provide a city name."
            )

    # ========================================================
    # 5-DAY FORECAST
    # ========================================================

    elif (
        "forecast" in lower
        or "next 5 days" in lower
        or "next five days" in lower
    ):

        city = extract_weather_city(
            user_message
        )

        if not city:

            city = get_previous_weather_city(
                session_id
            )

        if city:

            reply = AVAILABLE_FUNCTIONS[
                "get_weather_forecast"
            ](
                city
            )

        else:

            reply = (
                "Please provide a city name."
            )

    # ========================================================
    # CURRENT WEATHER
    # ========================================================

    elif (
        "weather" in lower
        or "temperature" in lower
        or "hot" in lower
    ):

        city = extract_weather_city(
            user_message
        )

        if not city:

            city = get_previous_weather_city(
                session_id
            )

        if city:

            reply = AVAILABLE_FUNCTIONS[
                "get_weather"
            ](
                city
            )

        else:

            reply = (
                "Please provide a city name."
            )

    # ========================================================
    # GEMINI + RAG + FUNCTION CALLING
    # ========================================================

    else:

        context = retrieve_context(
            user_message
        )

        enhanced_history = f"""
Retrieved Knowledge Context:
{context}

Conversation History:
{history_text}
"""

        reply = run_gemini_with_tools(
            user_message,
            enhanced_history
        )

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if reply is None:

        reply = (
            "Sorry, I could not generate a response "
            "right now. Please try again."
        )

    # ========================================================
    # SAVE ASSISTANT RESPONSE
    # ========================================================

    add_message(
        session_id,
        "assistant",
        reply
    )

    return reply
