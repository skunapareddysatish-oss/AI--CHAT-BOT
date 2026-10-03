from app.rag import ingest_documents, retrieve_context

ingest_documents()

query = "What is FastAPI?"

context = retrieve_context(query)

print("\nRetrieved Context:\n")
print(context)