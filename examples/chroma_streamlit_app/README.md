# RAG Search + Local LLM — Quick Start

## What it does

Index documents → Query them → Get AI answers from your **local Ollama** model.

## Architecture

```
Documents (team.txt, products.txt, about.txt)
        │
        ▼  (chunk + embed)
   ChromaDB (vector store)
        │
        ▼  (hybrid keyword + vector query)
   Top-K matching chunks
        │
        ▼  (RAG prompt: system + user)
   Ollama LLM (qwen3:8b / gpt-oss:20b / etc.)
        │
        ▼
   AI-generated answer with source citations
```

## Quick Start

### 1. Start Ollama on your Mac Mini

On the **Mac Mini** (hostname: `Nagarajus-Mac-mini.local`, IP: `192.168.1.198`):

```bash
# Install Ollama if not installed
brew install ollama

# Pull a model (pick one)
ollama pull qwen3:8b
# or: ollama pull gpt-oss:20b

# Start the server (default port 11434)
ollama serve
```

### 2. Launch the Streamlit app

On your **local machine**:

```bash
cd /Users/nagaraju/Documents/nagaraju/github/ragcheckup/examples/chroma_streamlit_app

# Point to your Mac Mini's Ollama
streamlit run app.py
```

In the app sidebar, change:
- **Ollama endpoint**: `http://192.168.1.198:11434/v1`
- **Model**: Select from your available models (e.g., `qwen3`, `gpt-oss`)
- **Temperature**: 0.0 (factual) to 0.7 (creative)

### 3. Use it

1. Click **📌 Index Documents** to build the knowledge base
2. Type a question in the chat input
3. Get an AI answer sourced from your documents

## Default endpoint (when Ollama runs locally)

If Ollama runs on your current machine:
- Endpoint: `http://localhost:11434/v1`
- Models: `qwen3:8b`, `gpt-oss:20b`, `deepseek-r1:8b`, `gemma4`, `deepseek-coder:33b`, `glm-4.7-flash`

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Documents directory | `./sample_docs/` | Folder with .txt/.md files |
| Chroma persist dir | `~/.chroma_rag/` | Vector store location |
| Top-K | 3 | Number of chunks to retrieve |
| Keyword match | False | Boost chunks containing query keywords |
| Ollama endpoint | `http://localhost:11434/v1` | Your Ollama server URL |
| Model | `qwen3:8b` | LLM to use for answer generation |
| Temperature | 0.0 | 0 = exact, 1 = creative |
| Max response tokens | 1024 | Output length limit |

## Sample Documents

Three company documents about "NexusAI" — a fictional AI company:
- **team.txt** — Leadership bios (CEO, CTO, VPE, Head of Data Science)
- **products.txt** — Three products (InsightEngine, DocuSight, PatientVoice)
- **about.txt** — Company history and reach

Try: *"Who is the CEO?"*, *"What products does NexusAI offer?"*, *"Where is NexusAI based?"*
