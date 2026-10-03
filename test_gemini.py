import os
from dotenv import load_dotenv
from google import genai


# Load .env
load_dotenv()


# Get Gemini API key
api_key = os.getenv("GEMINI_API_KEY")


print("=================================")
print("        GEMINI API TEST")
print("=================================")

print("API key loaded:", bool(api_key))


if not api_key:
    print()
    print("ERROR: GEMINI_API_KEY was not found in .env")
    print()
    exit()


print("Creating Gemini client...")


client = genai.Client(
    api_key=api_key
)


print("Gemini client created.")
print("Sending request to Gemini...")
print()


try:

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Say hello in one short sentence."
    )


    print("=================================")
    print("GEMINI RESPONSE")
    print("=================================")

    print(response.text)

    print("=================================")


except Exception as e:

    print("=================================")
    print("GEMINI ERROR")
    print("=================================")

    print("Error type:", type(e).__name__)
    print("Error:", str(e))

    print("=================================")