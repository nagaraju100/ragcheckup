# ragcheckup

**Eval tools tell you your score dropped. ragcheckup tells you which chunks are broken and why.**

ragcheckup is an open-source CLI and Python library that inspects the index behind a RAG
system (a chunk export file or a live vector database) and reports the structural
problems that make retrieval fail in production: shredded tables, chunks that lost their
context, exact-string lookups that vector search misses, conflicting document versions,
and basic index hygiene. Every finding points at specific chunk IDs and links to a fix.

> **Status:** Alpha (M1–M5 core features implemented, 83 tests passing). See the checks reference below.

## Quick start

```bash
# Install from source (PyPI release coming soon)
git clone https://github.com/nagaraju100/ragcheckup && cd ragcheckup
pip install .

# Scan a JSON/JSONL chunk export
ragcheckup scan corpus/chunks_naive.jsonl

# Full scan with BM25 vs. vector comparison (requires embed extra)
pip install ".[embed]"
ragcheckup scan corpus/chunks_naive.jsonl --embed-model all-MiniLM-L6-v2

# Scan the "good" index (mostly clean) for comparison
ragcheckup scan corpus/chunks_good.jsonl

# Scan a live Chroma collection (requires chroma extra)
pip install ".[chroma]"
ragcheckup scan chroma:///path/to/chroma_db/collection_name

# JSON report for CI
ragcheckup scan chunks.jsonl --format json --output report.json

# HTML report (dark theme, client-side filtering, self-contained)
ragcheckup scan chunks.jsonl --format html --output report.html

# List all available checks
ragcheckup checks
```

## What it finds

| Failure Mode | What it checks (one line each) |
|---|---|
| **Tables** | Are there broken Markdown tables? (missing column separators, inconsistent columns) |
| **Context** | Are chunks split in the middle of sentences? (missing headings, dangling references, orphan chunks, unusually small or large chunks) |
| **Exact** | Can exact identifiers (SKUs, error codes, ticket IDs) be found? Compares keyword (BM25) vs. vector search miss rates — tells you how much value adding vectors actually brings. |
| **Versions** | Is the system serving the latest content? (missing date/version metadata, stale content mixed with new, duplicate files with conflicting dates) |
| **Hygiene** | Is the index clean? (empty chunks, duplicate chunks wasting space, PDF extraction noise like repeated headers) |

## Install extras

```bash
pip install .                          # core checks, JSON/JSONL
pip install ".[chroma]"                # + Chroma connector
pip install ".[embed]"                # + sentence-transformers (exact-string check)
pip install ".[all]"                  # chroma + embed (everything implemented)
```

**Coming soon:** LLM-powered query evaluation (litellm integration).

## CLI options

```bash
# Config file (YAML)
ragcheckup scan chunks.jsonl --config ragcheckup.yaml

# Only run specific checks
ragcheckup scan chunks.jsonl --checks context.dangling_reference,table.flattened_numeric

# Skip checks
ragcheckup scan chunks.jsonl --skip hygiene.exact_duplicate

# CI gate: exit 1 if high-severity findings
ragcheckup scan chunks.jsonl --fail-on high --format json --output report.json
```

## Examples

- [`examples/rag_basics`](examples/rag_basics) — minimal RAG pipeline (chunk, embed, retrieve) to produce an index to scan.
- [`examples/chroma_streamlit_app`](examples/chroma_streamlit_app) — Streamlit + Chroma + Ollama demo app.
- [`examples/chroma_local_llm_app`](examples/chroma_local_llm_app) — same, with OpenAI-compatible gateway and API-key support.

## Design


- [**All 15 checks — complete reference table**](docs/CHECKS_REFERENCE.md) — what each check does, scope, severity, and why it matters
- [Planted test corpus](corpus/README.md) — 35 documents with problems planted on purpose

## Acknowledgements

The baseline structural checks are inspired by
[ChunkLint](https://github.com/prabhath004/chunkLint) (MIT).

## License

[MIT](LICENSE)
