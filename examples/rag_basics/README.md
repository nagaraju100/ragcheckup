# Simple RAG Example

A zero-dependency-on-APIs RAG (Retrieval-Augmented Generation) example. Uses only local ML libraries.

## What's inside

```
examples/rag_basics/
├── documents/              # Sample text documents for retrieval
│   ├── 1_what_is_llm.txt   # About Large Language Models
│   └── 2_rag_explained.txt # About RAG techniques
├── rag_pipeline.py         # Core: chunker, embedding, FAISS index, retriever
└── rag_cli.py              # CLI: single-shot or interactive mode
```

## Requirements

```bash
pip install sentence-transformers faiss-cpu
```

- `sentence-transformers` — embeds text into vectors (model: all-MiniLM-L6-v2)
- `faiss-cpu` — fast nearest-neighbor search

## Usage

**One-shot query:**

```bash
python rag_cli.py "What is RAG?"
```

**Interactive mode:**

```bash
python rag_cli.py
```

## How it works

1. **Chunking** — Documents are split into paragraphs, merged until ~300 tokens each.
2. **Embedding** — Each chunk is embedded using `all-MiniLM-L6-v2` (384-dim vectors).
3. **Indexing** — Vectors are stored in a FAISS `IndexFlatIP` (inner-product index).
4. **Retrieval** — User query is embedded and the top-3 most similar chunks are retrieved via cosine similarity.
5. **Response** — Retrieved chunks are displayed as context. (A generative LLM can be connected on top.)

## Extending this

To add generation, connect any LLM (local Ollama, OpenAI, Claude API) and pass `combined_context` from the `RAGResult` as prompt context.
