# ragcheckup

**Eval tools tell you your score dropped. ragcheckup tells you which chunks are broken and why.**

ragcheckup is an open-source CLI and Python library that inspects the index behind a RAG
system (a chunk export file or a live vector database) and reports the structural
problems that make retrieval fail in production: shredded tables, chunks that lost their
context, exact-string lookups that vector search misses, conflicting document versions,
and basic index hygiene. Every finding points at specific chunk IDs and links to a fix.

> **Status:** Alpha (M1 — core engine + baseline checks implemented). See the design
> documents below.

## Quick start

```bash
# Install (core checks, no LLM or embeddings needed)
pip install .

# Scan a JSON/JSONL chunk export
ragcheckup scan chunks.jsonl

# Scan a live Chroma collection (requires chroma extra)
pip install "ragcheckup[chroma]"
ragcheckup scan chroma:///path/to/chroma_db/collection_name

# JSON report for CI
ragcheckup scan chunks.jsonl --format json --output report.json

# List all available checks
ragcheckup checks
```

## What it finds

| Failure Mode | Checks | Severity |
|---|---|---|
| **Tables** (`table.*`) | Flattened numeric chunks, broken Markdown tables, orphan headers | High–Medium |
| **Context** (`context.*`) | Missing headings, dangling references, mid-sentence chunks, size outliers | High–Low |
| **Versions** (`version.*`) | Near-duplicates, same-title multiple dates, missing freshness metadata | Medium–Low |
| **Hygiene** (`hygiene.*`) | Exact duplicates, missing ID/source, empty or noisy chunks | High–Low |

## Install extras

```bash
pip install ragcheckup                 # core checks, JSON/JSONL
pip install "ragcheckup[chroma]"       # + Chroma connector
pip install "ragcheckup[embed]"        # + sentence-transformers (exact-string check)
pip install "ragcheckup[llm]"          # + litellm (evalset command)
pip install "ragcheckup[all]"          # everything
```

## Design

- [Product requirements](docs/PRD.md)
- [Technical design](docs/TECHNICAL_DESIGN.md)

## Acknowledgements

The baseline structural checks are inspired by
[ChunkLint](https://github.com/prabhath004/chunkLint) (MIT).

## License

[MIT](LICENSE)
