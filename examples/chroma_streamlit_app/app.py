"""Streamlit RAG Application — ChromaDB + FAISS + Local LLM (Ollama).

Index documents, query them, and get AI-generated answers from a local
Ollama instance via its OpenAI-compatible API.

Usage:
    streamlit run app.py [--docs-dir <path>] [--chroma-persist <path>]
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import requests
import sentence_transformers
import streamlit as st
from chromadb.config import Settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COLLECTION_NAME = "chunks"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_TOKENS = 300  # approximate word budget per chunk
TOP_K = 3
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"  # default when remote Mac Mini is configured

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, max_tokens: int = MAX_TOKENS) -> List[str]:
    """Split text on paragraph boundaries, merge until max_tokens."""
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        token_est = len(para.split())  # word-count ≈ token approximation
        if current_len + token_est > max_tokens and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(para)
        current_len += token_est

    if current:
        chunks.append("\n".join(current))

    return chunks


# ---------------------------------------------------------------------------
# ChromaDB helpers (unchanged)
# ---------------------------------------------------------------------------
def get_chroma_client(persist_dir: str) -> chromadb.ClientAPI:
    """Get (or create) a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=persist_dir)


def get_or_create_collection(
    client: chromadb.ClientAPI,
    embedder: sentence_transformers.SentenceTransformer,
) -> chromadb.Collection:
    """Get existing collection or create a new one."""
    try:
        return client.get_collection(COLLECTION_NAME)
    except (chromadb.errors.NotFoundError, KeyError):
        class EmbeddingFn:
            def __call__(self, input):
                return embedder.encode(input, normalize_embeddings=True).tolist()
        return client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=EmbeddingFn(),
        )


def index_documents(
    client: chromadb.ClientAPI,
    embedder: sentence_transformers.SentenceTransformer,
    docs_dir: str,
) -> Dict[str, int]:
    """Read all .txt/.md files, chunk, embed, and store in ChromaDB."""
    doc_path = Path(docs_dir)
    files = sorted(doc_path.glob("**/*.txt")) + sorted(doc_path.glob("**/*.md"))

    all_chunks: List[str] = []
    all_sources: List[str] = []
    all_chunk_indices: List[int] = []

    for fpath in files:
        text = fpath.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        for idx, chunk_text_ in enumerate(chunks):
            all_chunks.append(chunk_text_)
            all_sources.append(str(fpath.name))
            all_chunk_indices.append(idx)

    if not all_chunks:
        return {"indexed": 0, "files": 0}

    embeddings = embedder.encode(all_chunks, normalize_embeddings=True).tolist()

    ids = [f"{fpath.name}_chunk{idx}" for fpath, idx in zip(files, all_chunk_indices)]
    seen: Dict[str, int] = {}
    unique_ids = []
    for orig_id in ids:
        if orig_id in seen:
            seen[orig_id] += 1
            unique_ids.append(f"{orig_id}_v{seen[orig_id]}")
        else:
            seen[orig_id] = 0
            unique_ids.append(orig_id)

    collection = get_or_create_collection(client, embedder)

    collection.add(
        ids=unique_ids,
        documents=all_chunks,
        metadatas=[
            {"source": src, "chunk_index": cidx, "num_tokens": len(t.split())}
            for src, cidx, t in zip(all_sources, all_chunk_indices, all_chunks)
        ],
        embeddings=embeddings,
    )

    return {"indexed": len(all_chunks), "files": len(files)}


def query_chroma(
    client: chromadb.ClientAPI,
    embedder: sentence_transformers.SentenceTransformer,
    query_text: str,
    top_k: int = TOP_K,
) -> List[Dict]:
    """Query ChromaDB and return top-K matching chunks."""
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except (chromadb.errors.NotFoundError, KeyError):
        return []

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
    )

    items = []
    for i in range(len(results["ids"][0])):
        items.append({
            "source": results["metadatas"][0][i].get("source", "unknown"),
            "chunk_index": results["metadatas"][0][i].get("chunk_index", -1),
            "text": results["documents"][0][i],
            "distance": float(results["distances"][0][i]) if results["distances"] else 0.0,
        })

    return items


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from a query string."""
    stop_words = {
        "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
        "of", "or", "and", "but", "what", "who", "which", "where",
        "when", "why", "how", "did", "do", "does", "was", "are",
        "were", "be", "been", "by", "with", "that", "this", "these",
        "those", "from", "has", "had", "have", "not", "no", "so",
        "if", "then", "than", "as", "into", "over", "after",
        "all", "any", "both", "each", "few", "more", "most",
        "other", "some", "such", "too", "very", "just", "about",
    }
    words = text.lower().split()
    return [w for w in words if w not in stop_words and len(w) > 1]


def query_with_keywords(
    client: chromadb.ClientAPI,
    embedder: sentence_transformers.SentenceTransformer,
    query_text: str,
    top_k: int = TOP_K,
    use_keywords: bool = False,
) -> List[Dict]:
    """Query ChromaDB with optional keyword filtering."""
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except (chromadb.errors.NotFoundError, KeyError):
        return []

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k * 2 if use_keywords else top_k,
    )

    keywords = _extract_keywords(query_text)
    items = []
    for i in range(len(results["ids"][0])):
        chunk_text = results["documents"][0][i]
        chunk_lower = chunk_text.lower()
        matched_keywords = [kw for kw in keywords if kw in chunk_lower]
        keyword_score = len(matched_keywords) / max(len(keywords), 1)

        distance = float(results["distances"][0][i]) if results["distances"] else 0.0

        if use_keywords and keywords:
            effective_distance = distance * (1 / (1 + keyword_score))
        else:
            effective_distance = distance

        items.append({
            "source": results["metadatas"][0][i].get("source", "unknown"),
            "chunk_index": results["metadatas"][0][i].get("chunk_index", -1),
            "text": chunk_text,
            "distance": distance,
            "keyword_score": keyword_score,
            "matched_keywords": matched_keywords,
            "_effective_distance": effective_distance,
        })

    if use_keywords and keywords:
        items.sort(key=lambda x: x["_effective_distance"])
        items = items[:top_k]

    for item in items:
        item.pop("_effective_distance", None)

    return items


# ---------------------------------------------------------------------------
# Ollama / Local LLM client
# ---------------------------------------------------------------------------
def ollama_chat(
    endpoint: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 2048,
    timeout_s: int = 120,
) -> Dict[str, Any]:
    """Call Ollama OpenAI-compatible chat API.

    Parameters
    ----------
    endpoint : str
        e.g. ``http://localhost:11434/v1`` or ``http://192.168.1.198:11434/v1``
    model : str
        e.g. ``qwen3:8b``, ``gpt-oss:20b``, ``deepseek-r1:8b``
    messages : list[dict]
        OpenAI-style ``[{ "role": "user"/"assistant"/"system", "content": "..." }]``
    temperature : float
        0.0 = deterministic, 1.0 = creative
    max_tokens : int
        Maximum output tokens
    timeout_s : int
        Seconds to wait for a response

    Returns
    -------
    dict with keys: ``content`` (str), ``model`` (str), ``done`` (bool),
    ``total_duration`` (ns), ``prompt_eval_count``, ``eval_count``.
    """
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,  # simple non-streaming mode
    }

    resp = requests.post(
        f"{endpoint}/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=timeout_s,
    )
    resp.raise_for_status()
    data = resp.json()

    choice = data["choices"][0]
    return {
        "content": choice["message"]["content"],
        "model": data.get("model", model),
        "done": choice.get("finish_reason", "stop") == "stop",
        "total_duration_ns": data.get("total_duration", 0),
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "eval_count": data.get("eval_count", 0),
    }


def list_ollama_models(endpoint: str) -> List[str]:
    """Return available model names from Ollama."""
    try:
        resp = requests.get(f"{endpoint}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


def build_rag_prompt(query: str, chunks: List[Dict]) -> str:
    """Build the system + user prompt for RAG.

    The prompt tells the LLM to answer **only** from the provided context,
    and to cite the source document for each fact.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[{chunk['source']}, chunk {chunk['chunk_index']}, "
            f"distance={chunk['distance']:.4f}]\n{chunk['text']}"
        )
    context = "\n\n---\n".join(context_parts)

    system = (
        "You are a helpful assistant. Answer the user's question using ONLY "
        "the provided context below. If the context doesn't contain enough "
        "information to answer, say so — don't invent facts. When you use "
        "information from a source, cite it by filename (e.g. 'products.txt'). "
        "Be concise and precise.\n\n"
        "--- CONTEXT ---\n"
        f"{context}\n"
        "--- END CONTEXT ---"
    )

    return system, f"Question: {query}\n\nPlease answer using the context above."


# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------
def main():
    default_docs_dir = str(Path(__file__).parent / "sample_docs")
    default_chroma_dir = str(Path.home() / ".chroma_rag")

    st.set_page_config(
        page_title="RAG Search + LLM",
        page_icon="🔍",
        layout="wide",
    )

    st.title("🔍 RAG Search + Local LLM")
    st.caption(
        "Index documents, query them, and get AI-generated answers from "
        "your local Ollama instance."
    )

    # ---------------------------------------------------------------
    # Sidebar — Settings
    # ---------------------------------------------------------------
    st.sidebar.header("⚙️ Settings")

    docs_dir = st.sidebar.text_input(
        "📂 Documents directory", value=default_docs_dir
    )
    chroma_dir = st.sidebar.text_input(
        "💾 Chroma persist directory", value=default_chroma_dir
    )
    top_k = st.sidebar.slider("📊 Top-K results", 1, 10, TOP_K)
    use_keywords = st.sidebar.checkbox("🔑 Keyword match", value=False)
    if use_keywords:
        st.sidebar.caption("Chunks containing query keywords are boosted.")

    # ---------------------------------------------------------------
    # Sidebar — Ollama / LLM Settings
    # ---------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("🤖 LLM Settings")

    ollama_endpoint = st.sidebar.text_input(
        "🔗 Ollama endpoint",
        value=DEFAULT_OLLAMA_ENDPOINT,
        help="e.g. http://localhost:11434/v1 or "
             "http://192.168.1.198:11434/v1 (Mac Mini)",
    )
    st.sidebar.caption(
        f"Tip: Mac Mini hostname is "
        f"**Nagarajus-Mac-mini.local** at "
        f"**http://192.168.1.198:11434/v1**"
    )

    # Discover available models
    available_models = list_ollama_models(ollama_endpoint)
    if available_models:
        default_model = DEFAULT_OLLAMA_MODEL
        if default_model in available_models:
            default_model = default_model
        elif available_models:
            default_model = available_models[0]
        else:
            default_model = "qwen3:8b"
    else:
        default_model = DEFAULT_OLLAMA_MODEL

    ollama_model = st.sidebar.selectbox(
        "📦 Model",
        options=available_models if available_models else ["qwen3:8b", "gpt-oss:20b", "deepseek-r1:8b"],
        index=0 if available_models else 0,
        help="Select a model available on your Ollama instance.",
    )

    temperature = st.sidebar.slider(
        "🌡️ Temperature", 0.0, 1.0, 0.0, 0.01,
        help="0.0 = deterministic, 1.0 = creative",
    )
    max_response_tokens = st.sidebar.slider(
        "📝 Max response tokens", 128, 4096, 1024, 64,
    )

    # Connection status
    if available_models:
        st.sidebar.success(f"✅ Connected — {len(available_models)} model(s) found")
    else:
        st.sidebar.warning(
            "⚠️ Could not reach Ollama at "
            f"**{ollama_endpoint}**. "
            "Ensure Ollama is running on the target machine."
        )

    # ---------------------------------------------------------------
    # Sidebar — Index Management (unchanged)
    # ---------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("📚 Index Management")

    col1, col2 = st.sidebar.columns(2)

    with col1:
        index_btn = st.button(
            "📌 Index Documents", type="primary", use_container_width=True
        )

    with col2:
        clear_btn = st.button("🗑️ Clear Index", use_container_width=True)

    # Handle clear
    if clear_btn:
        if st.sidebar.button("✅ Confirm clear?", key="confirm_clear"):
            if os.path.exists(chroma_dir):
                import shutil
                shutil.rmtree(chroma_dir)
            st.session_state["indexed"] = 0
            st.session_state["file_count"] = 0
            if "chat_history" in st.session_state:
                st.session_state["chat_history"] = []
            st.sidebar.success("Index cleared.")
            st.rerun()

    # Handle index
    indexed = st.session_state.get("indexed", 0)
    file_count = st.session_state.get("file_count", 0)

    if index_btn and docs_dir:
        try:
            docs_path = Path(docs_dir)
            if not docs_path.exists():
                st.sidebar.error(f"Directory not found: {docs_dir}")
            elif not any(docs_path.glob("**/*.txt")) and not any(docs_path.glob("**/*.md")):
                st.sidebar.warning("No .txt or .md files found in this directory.")
            else:
                emb = get_embedder()
                client = get_chroma_client(chroma_dir)
                result = index_documents(client, emb, docs_dir)
                st.session_state["indexed"] = result["indexed"]
                st.session_state["file_count"] = result["files"]
                st.sidebar.success(
                    f"Indexed {result['indexed']} chunks from "
                    f"{result['files']} files."
                )
        except Exception as e:
            st.sidebar.error(f"Indexing failed: {e}")
            st.error(e)

    # Show index status
    if indexed > 0:
        st.sidebar.success(f"✅ Index: {indexed} chunks from {file_count} files")
    elif indexed == 0 and file_count == 0:
        st.sidebar.info("Click 'Index Documents' to build the index.")

    # ---------------------------------------------------------------
    # Chat interface
    # ---------------------------------------------------------------
    st.header("💬 Chat with Your Documents")

    # Embedding model — lazy init
    embedder: Optional[sentence_transformers.SentenceTransformer] = None

    def get_embedder():
        nonlocal embedder
        if embedder is None:
            embedder = sentence_transformers.SentenceTransformer(MODEL_NAME)
        return embedder

    # Chat history (persists across reruns)
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Container for chat messages
    chat_container = st.container()

    # Display past messages
    with chat_container:
        for msg in st.session_state["chat_history"]:
            role = msg["role"]
            content = msg["content"]
            with st.chat_message(role):
                st.markdown(content)
                # Show retrieved chunks if this was a query
                if role == "user" and "retrieved" in msg:
                    with st.expander("📄 Retrieved context", expanded=False):
                        for chunk in msg["retrieved"]:
                            st.markdown(
                                f"**{chunk['source']}** (chunk "
                                f"{chunk['chunk_index']}, "
                                f"dist={chunk['distance']:.4f})"
                            )
                            st.markdown(f"> {chunk['text'][:400]}")
                            st.divider()

    # Query input
    query = st.chat_input(
        "Ask a question — the retrieved chunks will be fed to your local LLM"
    )

    if query and indexed > 0:
        try:
            client = get_chroma_client(chroma_dir)

            # Step 1: Retrieve chunks
            results = query_with_keywords(
                client, get_embedder(), query, top_k, use_keywords,
            )

            if not results:
                st.info(
                    "No matching chunks found. Try indexing documents first, "
                    "or rephrase your question."
                )
            else:
                # Step 2: Build RAG prompt and call LLM
                system_prompt, user_prompt = build_rag_prompt(query, results)

                # Build messages list with chat history context
                messages = [
                    {"role": "system", "content": system_prompt},
                ]
                # Add previous turns (last 4 messages to keep context manageable)
                recent_chat = st.session_state["chat_history"][-8:]
                for msg in recent_chat:
                    if msg["role"] == "user" and msg.get("content") != query:
                        messages.append(
                            {"role": "user", "content": msg["content"]}
                        )
                    elif msg["role"] == "assistant":
                        messages.append(
                            {"role": "assistant", "content": msg["content"]}
                        )
                messages.append({"role": "user", "content": user_prompt})

                # Show loading
                with st.chat_message("assistant"):
                    with st.spinner("🔍 Retrieving chunks + querying LLM..."):
                        t0 = time.time()

                        llm_result = ollama_chat(
                            endpoint=ollama_endpoint,
                            model=ollama_model,
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_response_tokens,
                        )

                        elapsed = time.time() - t0
                        tokens_used = (
                            llm_result.get("prompt_eval_count", 0)
                            + llm_result.get("eval_count", 0)
                        )

                answer = llm_result["content"]

                # Display answer
                st.markdown(answer)

                # LLM metadata
                with st.expander("📊 LLM Response Details", expanded=False):
                    st.caption(
                        f"Model: **{llm_result['model']}** | "
                        f"Response tokens: "
                        f"{llm_result.get('eval_count', 'N/A')} | "
                        f"Prompt tokens: "
                        f"{llm_result.get('prompt_eval_count', 'N/A')} | "
                        f"Total: ~{tokens_used} tokens | "
                        f"Latency: {elapsed:.1f}s"
                    )

                    # Show chunks fed to LLM
                    st.markdown("**Chunks fed to LLM:**")
                    for i, chunk in enumerate(results, 1):
                        st.markdown(
                            f"{i}. **{chunk['source']}** "
                            f"(chunk {chunk['chunk_index']})"
                        )
                        st.markdown(f"> {chunk['text'][:300]}")

                # Save to history
                st.session_state["chat_history"].append({
                    "role": "user",
                    "content": query,
                    "retrieved": results,
                })
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": answer,
                })

        except Exception as e:
            st.error(f"Query failed: {e}")
            st.exception(e)

    elif not indexed:
        st.info(
            "No index available. Click **'Index Documents'** in the sidebar "
            "to build the knowledge base first."
        )

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Built with Streamlit + ChromaDB + SentenceTransformers + Ollama\n"
        f"Embedding: {MODEL_NAME} | Chunks: ~{MAX_TOKENS} tokens\n"
        f"LLM: {ollama_model} via {ollama_endpoint}"
    )


# Lazy embedder helper (extracted for index function)
_embedder_instance: Optional[sentence_transformers.SentenceTransformer] = None


def get_embedder() -> sentence_transformers.SentenceTransformer:
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = sentence_transformers.SentenceTransformer(MODEL_NAME)
    return _embedder_instance


if __name__ == "__main__":
    main()
