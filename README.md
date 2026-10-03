# Nova — Advanced AI Workspace

Nova is a memory-enabled FastAPI chatbot with a polished web workspace. It combines Gemini responses with function calling, weather, calculator, order lookup, Wikipedia and Tavily web search, SQLite conversation history, and an optional Chroma knowledge base.

## Run locally

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add `GEMINI_API_KEY`. Weather and Tavily keys are optional.

3. Start the server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open <http://localhost:8000>.

The API also exposes `/health`, `/docs`, `/chat`, `/history/{session_id}`, and `/conversations`.

## Deploy to Render

The repository includes `render.yaml`. Create a new Blueprint on Render and select this project. Render will install the requirements, start Uvicorn, run the `/health` check, and mount a small persistent disk for SQLite and Chroma data. Add the provider keys when Render prompts for secret environment variables.

For another platform, use:

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Keep `.env` and all provider keys in the platform's secret environment-variable settings; never commit them.

## Knowledge base

Place `.txt`, `.md`, or `.pdf` files in `data/docs`. When Gemini is configured, the app indexes those files on startup and retrieves relevant chunks for general questions. Chroma and SQLite paths can be redirected with `CHROMA_PATH` and `DB_PATH` for persistent cloud storage.
