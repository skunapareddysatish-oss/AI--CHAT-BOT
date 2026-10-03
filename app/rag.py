import os

try:
    import chromadb
except ImportError:  # pragma: no cover - deployment installs the dependency
    chromadb = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - deployment installs the dependency
    PdfReader = None

from app.config import CHROMA_PATH, COLLECTION_NAME, DOCUMENTS_PATH
from app.embeddings import embed

collection = None
if chromadb is not None:
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    except Exception:
        # Chroma is an optional enhancement.  A bad or read-only index should
        # not prevent the main assistant from serving requests.
        collection = None


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    """
    Split text into overlapping chunks.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


def ingest_documents(folder: str = "data/docs"):
    """
    Read all PDF, TXT and MD files from data/docs
    and store their embeddings in ChromaDB.
    """

    folder_path = folder if os.path.isabs(folder) else str(DOCUMENTS_PATH)
    if not os.path.isdir(folder_path) or collection is None:
        return 0

    indexed = 0
    for filename in os.listdir(folder_path):
        path = os.path.join(folder_path, filename)

        if filename.endswith(".pdf") and PdfReader is not None:
            reader = PdfReader(path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)

        elif filename.endswith((".txt", ".md")):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

        else:
            continue

        chunks = chunk_text(text)

        embeddings = embed(chunks)
        if not embeddings:
            continue

        ids = [f"{filename}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": filename} for _ in chunks]

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
        )

        indexed += len(chunks)

    return indexed


def retrieve_context(query: str, k: int = 4):
    """
    Retrieve the most relevant document chunks.
    """

    if collection is None:
        return ""

    query_embeddings = embed([query])
    if not query_embeddings:
        return ""

    query_embedding = query_embeddings[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    if results.get("documents") and results["documents"][0]:
        return "\n\n---\n\n".join(results["documents"][0])

    return ""
