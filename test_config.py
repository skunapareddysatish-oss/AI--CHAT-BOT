from app.config import client, CHAT_MODEL

response = client.models.generate_content(
    model=CHAT_MODEL,
    contents="Say hello in one sentence."
)

print(response.text)