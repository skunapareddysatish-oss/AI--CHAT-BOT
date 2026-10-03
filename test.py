import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

print("API Key:", os.getenv("GEMINI_API_KEY"))

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

response = client.models.generate_content(
    model="gemini-flash-latest",
    contents="Hello"
)

print(response.text)