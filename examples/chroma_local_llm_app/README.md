# RAG Search + Local LLM — Ollama Integration

ChromaDB vector retrieval + local Ollama LLM answer generation.

## Quick Start

### 1. Start Ollama on your Mac Mini

On the **Mac Mini** (IP: `192.168.1.198`):

```bash
brew install ollama
ollama pull qwen3:8b    # or gpt-oss:20b, deepseek-r1:8b
ollama serve
```

### 2. Launch the Streamlit app

```bash
cd /Users/nagaraju/Documents/nagaraju/github/ragcheckup/examples/chroma_local_llm_app
streamlit run app.py
```

In the app sidebar, set:
- **Ollama endpoint**: `http://192.168.1.198:11434/v1` (Mac Mini)
- **Model**: Select from available models

### 3. Use it

1. Click **📌 Index Documents**
2. Type a question in the chat
3. Get AI answer with source citations

## Sample Documents

- `team.txt` — Leadership bios
- `products.txt` — Products (InsightEngine, DocuSight, PatientVoice)
- `about.txt` — Company history

Try: "Who is the CEO?", "What products does NexusAI offer?"

## API Key

```bash
cp .env.example .env   # then set OLLAMA_API_KEY=<your key>
```

`.env` is git-ignored. The key is sent as `Authorization: Bearer <key>`; you can also paste it in the sidebar.
