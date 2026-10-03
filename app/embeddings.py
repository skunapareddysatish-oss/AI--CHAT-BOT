from app.config import client, EMBED_MODEL

def embed(texts):
    if not texts or client is None:
        return []

    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts
    )

    return [e.values for e in response.embeddings]
