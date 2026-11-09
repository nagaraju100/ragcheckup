# ragcheckup — Product Requirements Document

| | |
|---|---|
| Status | Draft for approval |
| Author | Nagaraju (owner), drafted with Claude |
| Date | 2026-11-08 |
| Working name | `ragcheckup` (see "Decisions made by the drafter") |
| Companion doc | [TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) |

## 1. Summary

`ragcheckup` is an open-source command-line tool and Python library that inspects the
**index behind a RAG system** — the chunks and their metadata, in an export file or in a
live vector database — and reports the structural problems that make retrieval fail in
production. It finds problems *before* users hit them, points at the exact chunks
involved, and links each finding to a plain-language fix.

One-line pitch: **"Eval tools tell you your score dropped. ragcheckup tells you which
chunks are broken and why."**

## 2. Problem

Teams ship RAG chatbots that work in a demo and degrade with real users and real
documents. The causes are mostly in the index, not the model. The Systems in Prod article
*"Your RAG demo worked. Here's what breaks with real users."* names five recurring
failures:

1. **Shredded tables** — parsers flatten tables into streams of numbers with no headers,
   so no question ever matches them.
2. **Chunks lose their context** — "This limit is 30 days" with the heading that said
   *which* limit cut off into a previous chunk.
3. **Exact strings** — users search for error codes, SKUs, ticket numbers and names;
   pure vector search is weak at these.
4. **Old and new versions disagree** — both the 2023 and 2025 policy are indexed, and the
   bot answers from the old one.
5. **No evaluation set** — changes ship on gut feel and silently break other questions.

Existing tools do not cover this well:

- **Evaluation and observability frameworks** (ragas, deepeval, promptfoo, langfuse, opik,
  phoenix) score question → context → answer triples. They tell you *that* quality
  dropped, not *which chunks* caused it, and they need questions to exist first.
- **Chunk linters** (ChunkLint, RAG Dataset Linter, ChunkScore, RAG-TUI) are small or
  early. The most complete, ChunkLint (MIT, Python), lints exported chunk files only. It
  explicitly is not a vector database scanner and not a retrieval evaluator, and its own
  documentation notes it has no labeled corpus backing its accuracy.
- **Staleness tools** (raghealth, RAG Staleness Check, ragfresh) are single-purpose and
  early-stage.

No tool covers all five failure modes, and none measures the exact-string blind spot.

## 3. Target users

- **Primary: the engineer who owns a RAG pipeline** at a company. Has an index (Chroma,
  Qdrant, pgvector, or a JSONL/Parquet export of chunks). Wants a fast answer to "what is
  wrong with my index?" and a CI gate that stops regressions.
- **Secondary: the owner (Nagaraju)**, who is new to building RAG apps. The project is
  also the learning path: building the planted test corpus and the checks teaches how
  RAG indexes fail. The tool must therefore be understandable end to end by its owner.
- **Tertiary: readers of Systems in Prod**, who arrive from the blog and want to try the
  fixes the articles describe.

## 4. Goals

1. Detect each of the five failure modes with a named check that points at specific
   chunk IDs and explains the fix.
2. Work on what users already have: a chunk export file, or a live vector database,
   without re-ingesting documents.
3. Run fully locally. The core structural checks need no LLM, no network and no API key.
4. Be CI-friendly: deterministic output, JSON report, configurable failure threshold,
   non-zero exit code.
5. Back every check's accuracy with a **labeled benchmark corpus** that ships in the repo,
   and publish precision and recall per check.
6. Complement, not replace, eval frameworks: export a starter evaluation set in formats
   ragas and deepeval can consume.
7. Be easy to adopt: `pipx install ragcheckup` and a first useful report within five
   minutes.

## 5. Non-goals

- Not an evaluation framework. It does not score LLM answers for faithfulness or
  relevance.
- Not an observability or tracing platform.
- Not a document parser or chunker. It inspects chunks; it does not create them
  (it may *suggest* fixes).
- Not a hosted service. No accounts, no telemetry.
- Not an index repair tool in v1. It reports; it does not delete or rewrite vectors.

## 6. Anti-goals (failure even if it technically works)

- **Noisy reports.** If a typical clean index produces pages of low-value findings, users
  will uninstall it. False positives are worse than misses for adoption.
- **Unexplained findings.** A finding without a reason and a fix is a failure.
- **Hidden network calls or cost.** Any check that calls an embedding API or LLM must be
  opt-in and say so before it runs.
- **Writes to the user's index.** Connectors are read-only, always.
- **A ChunkLint clone with a new name.** The baseline checks must be reimplemented
  independently and credited; the value is in what ChunkLint does not do.

## 7. The checks

Each check has an ID, the failure mode it targets, what it needs, and its default
severity. Severity levels: `high`, `medium`, `low`. The `scan` command reports five
**scored groups**: tables, context, exact, versions, and index hygiene. Failure 5 is a
separate command (`evalset`) and is not part of `scan` scoring.

### Failure 1 — Shredded tables

| ID | What it flags | Needs | Default severity |
|---|---|---|---|
| `table.flattened_numeric` | Chunks dominated by numeric tokens with few word tokens near them (rows of numbers with no labels), typical of flattened PDF tables | Text only | high |
| `table.markdown_broken` | Markdown tables with inconsistent column counts, missing header separator, or header with no rows | Text only | high |
| `table.header_orphan` | Header-like lines (short, title-cased tokens) with no data following in the same chunk | Text only | medium |

### Failure 2 — Lost context

| ID | What it flags | Needs | Default severity |
|---|---|---|---|
| `context.missing_heading` | No title/heading/section in metadata **and** none in the first lines of text | Text + metadata | medium |
| `context.dangling_reference` | Chunk opens with a reference to something not in the chunk ("This", "It", "These", "The above", "As mentioned") | Text only | medium |
| `context.starts_mid_sentence` | Chunk begins with a lowercase word or a connector ("and", "but", "which") | Text only | high |
| `context.ends_mid_sentence` | Chunk ends without terminal punctuation; raised to high when the next chunk of the same source confirms the split | Text + ordering | medium (high when confirmed) |
| `context.size_outlier` | Chunks far below or above the index's own size distribution (relative, not fixed thresholds) | Text only | low |

### Failure 3 — Exact-string blind spot (launch headline)

| ID | What it flags | Needs | Default severity |
|---|---|---|---|
| `exact.vector_miss_rate` | Extracts identifiers from the corpus itself (error codes, SKUs, ticket IDs, version strings, capitalized names), queries the index with each, and measures how often the chunk containing it is **not** in the top-k vector results, compared with a keyword (BM25) baseline | Embeddings for queries (see section 9) | high when vector misses exceed keyword misses by 30+ points; medium at 15+ |

Output always shows both raw miss rates; the gap between them drives severity and score.
Example: *"Vector search missed 62% of 214 exact-identifier lookups (keyword search
missed 4%). Your users' code and SKU searches will fail. Enable hybrid search."*

### Failure 4 — Version conflicts

| ID | What it flags | Needs | Default severity |
|---|---|---|---|
| `version.near_duplicate` | Near-identical chunks from **different** sources or different dates | Text (+ stored vectors if available) | medium |
| `version.same_title_multiple_dates` | Same document title or source stem indexed with more than one version/date | Metadata | medium (high when the versions also share near-duplicate chunks) |
| `version.missing_freshness_metadata` | Chunks with no version, last-updated or date metadata, reported as a share of the index | Metadata | low |

### Index hygiene (supports all failure modes)

| ID | What it flags | Needs | Default severity |
|---|---|---|---|
| `hygiene.exact_duplicate` | Byte-identical chunk text appearing more than once | Text only | medium |
| `hygiene.missing_id_or_source` | Chunks with no stable ID or no source reference | Metadata | medium |
| `hygiene.empty_or_noise` | Empty chunks and PDF extraction noise (page headers/footers repeated across many chunks, excessive line breaks) | Text only | high for empty, low for noise |

**High-severity checks** (subject to the quality targets in section 12):
`table.flattened_numeric`, `table.markdown_broken`, `context.starts_mid_sentence`,
`context.ends_mid_sentence` (confirmed splits), `version.same_title_multiple_dates`
(with shared chunks), `hygiene.empty_or_noise` (empty), `exact.vector_miss_rate`.

### Failure 5 — No evaluation set

| ID | What it does | Needs |
|---|---|---|
| `evalset` (separate command, produces no findings) | Generates a starter set of questions from a sample of chunks, runs retrieval hit@k for each, and exports the set for ragas and deepeval | An LLM (opt-in) and embeddings |

## 8. Inputs

| Source | v1 | Later |
|---|---|---|
| JSON / JSONL chunk export | Yes | |
| Parquet / CSV export | | Yes |
| Chroma (local persistent or HTTP) | Yes | |
| Qdrant | | Yes |
| pgvector | | Yes |
| LangChain `Document` list / LlamaIndex nodes (Python API) | | Yes |
| Pinecone, Weaviate, LanceDB | | Community |

## 9. What needs a model, honestly

| Checks | Needs |
|---|---|
| Failures 1, 2, 4 and hygiene | Nothing. Pure text and metadata. |
| Failure 3 (`exact.vector_miss_rate`) | The **same embedding model that built the index**, to embed the identifier queries. Without it the check is skipped with a clear message. |
| Failure 5 (`evalset.generate`) | An LLM to write questions (local via Ollama or a hosted API key), plus the embedding model. Opt-in only. |

## 10. User experience

```bash
pipx install ragcheckup

# Lint an export file
ragcheckup scan chunks.jsonl

# Lint a live Chroma collection
ragcheckup scan chroma://./chroma_db/policies

# Include the exact-string check
ragcheckup scan chroma://./chroma_db/policies --embed-model sentence-transformers/all-MiniLM-L6-v2

# CI gate
ragcheckup scan chunks.jsonl --fail-on high --format json --output report.json

# HTML report for humans
ragcheckup scan chunks.jsonl --format html --output report.html

# Starter evaluation set (opt-in LLM)
ragcheckup evalset chroma://./chroma_db/policies --llm ollama/llama3.1 --embed-model ... --out evalset/
```

Terminal output leads with a one-screen summary — a score per failure mode, the top
findings with chunk IDs, and a link to the fix — then details with `--verbose`.

## 11. The planted test corpus

A hand-written corpus of about 30 documents for a fictional company, with problems
planted on purpose and labeled:

- Tables rendered both correctly and flattened.
- Policies that exist in two versions with different dates.
- Long sections chunked so headings detach.
- Product codes, error codes and ticket IDs used throughout.
- A clean control set with no planted problems.

It has three jobs: the owner's hands-on way to learn RAG, the test fixture and
benchmark for every check, and the demo used in the README, video and launch post. It is
written from scratch (no scraped or copied content) so it can ship under the project
license.

## 12. Success metrics

**Quality (gates for each release):**

- Every check has precision and recall measured on the labeled corpus, published in the
  README. Measurement rules are in the technical design, section 14.
- v1 target: precision at least 0.9 and recall at least 0.8 for each high-severity check
  on the corpus; at most 5% of chunks in the clean control set flagged at any severity.

**Adoption (first 90 days after launch, aspirational):**

- 500 GitHub stars, 1,000 PyPI downloads per month, 5 external contributors, 3 public
  "we found X with ragcheckup" posts or issues.

**Owner outcomes:**

- The owner can explain every check and its trade-offs.
- At least two Systems in Prod articles and one YouTube video come out of the project.

## 13. Milestones

| Milestone | Scope | Exit criterion |
|---|---|---|
| **M0 — Test corpus** | Planted corpus, labels file, ingestion script into Chroma and JSONL | Corpus builds in one command; every planted problem has a label |
| **M1 — Core engine + baseline checks** | Loader for JSON/JSONL, check framework, failures 2 and hygiene checks, terminal + JSON report, config file, exit codes | All planted context problems flagged; clean set under 5% flagged |
| **M2 — Tables and versions** | Failure 1 and 4 checks | Targets in section 12 met for these checks |
| **M3 — Chroma connector** | Read-only scan of a live Chroma collection | Same findings from Chroma as from the JSONL export of the same corpus |
| **M4 — Exact-string check** | `exact.vector_miss_rate` with BM25 baseline | On the naive corpus index (built with the pinned corpus embedding model), the check extracts at least 90% of the planted identifiers, reports a vector-minus-keyword gap of at least 15 points, and gives identical numbers on two runs with the same seed; launch demo recorded |
| **M5 — Report + launch** | HTML report, README with GIF, docs site pages on Systems in Prod, PyPI release 0.1.0 | Fresh install to first report under five minutes on a clean machine |
| **M6 — Eval set** | `evalset` command with ragas and deepeval export | Exported files load in the current ragas and deepeval versions |
| **Later** | Qdrant, pgvector, Parquet, LangChain/LlamaIndex adapters, fix suggestions | |

Version 0.1.0 (the launch) is M0–M5. M6 follows as 0.2.0.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Heuristics are noisy on real indexes | Conservative defaults; relative (per-index) thresholds; measured against the clean control set; every rule can be disabled or tuned |
| Corpus is too synthetic, so benchmark numbers do not transfer | Add a second, real public corpus (for example open government policy documents with permissive licenses) before 0.2.0 |
| Exact-string check gives misleading numbers when the user's embedding model is not the index's model | Detect Chroma's stored embedding function; warn loudly when the model is user-supplied; print dimension mismatch errors |
| A big eval framework adds index linting | Stay focused, ship fast, integrate with them rather than compete |
| Owner is new to RAG | M0 corpus is the learning path; the design keeps every check small and readable |

## 15. Relationship to ChunkLint

ChunkLint (MIT, github.com/prabhath004/chunkLint) inspired the baseline structural checks.
ragcheckup reimplements those checks independently, credits ChunkLint in the README, and
keeps ChunkLint's MIT copyright notice on any code copied directly. Its rule
documentation and word lists are not copied verbatim.

## 16. Decisions made by the drafter (for the owner to confirm)

- Name `ragcheckup` — free on PyPI and GitHub as of 2026-11-08. PyPI has no reservation;
  the name is only secured by publishing, so a placeholder 0.0.1 release early in M1 is
  recommended.
- Simplicity over speed in 0.1.0: single process, readable code first.
- Corpus embedding model: `sentence-transformers/all-MiniLM-L6-v2`, pinned.
- Python, distributed on PyPI, installed with `pipx`.
- Chroma as the first live connector, because it runs locally with no server.
- License: Apache-2.0 (patent grant, common for infrastructure tools). MIT is the
  alternative if the owner prefers the simplest license.
- Project lives under the owner's GitHub account `nagaraju100`, with docs pages on
  systemsinprod.com.
