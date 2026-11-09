# ragcheckup — Technical Design Document

| | |
|---|---|
| Status | Approved by owner, 2026-11-08 |
| Date | 2026-11-08 |
| Requirements | [PRD.md](PRD.md) |

This document describes how ragcheckup is built. The PRD says *what* and *why*; this
says *how*. Choices marked **(drafter's call)** were not decided by the owner and can be
changed.

## 1. Architecture overview

```
            ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
 source ──▶ │  Connector   │ ──▶ │ Normalizer  │ ──▶ │ ChunkSet     │
 (file/DB)  │ (read-only)  │     │ (metadata   │     │ (in memory)  │
            └──────────────┘     │  key mapping│     └──────┬───────┘
                                 └─────────────┘            │
                                                            ▼
            ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
 report ◀── │  Reporters   │ ◀── │   Engine    │ ◀── │   Checks     │
 (term/JSON │ (terminal,   │     │ (runs checks│     │ (chunk-level,│
  /HTML)    │  JSON, HTML) │     │  aggregates)│     │  corpus-level│
            └──────────────┘     └─────────────┘     │  retrieval)  │
                                                     └──────────────┘
```

Data flows one way. Connectors never write. Checks are pure functions over a `ChunkSet`
(plus optional `Retriever` for retrieval checks), which makes each one easy to test in
isolation.

## 2. Technology choices

| Concern | Choice | Reason |
|---|---|---|
| Language | Python 3.10+ | RAG ecosystem is Python; owner's target stack **(drafter's call)** |
| Packaging | `pyproject.toml`, `hatchling` build backend, `uv` for dev | Standard, fast |
| CLI | `typer` | Typed, small, good help output |
| Terminal output | `rich` | Tables and colour without effort |
| Config and models | `pydantic` v2 | Validation, JSON schema for the report |
| Config file | YAML via `pyyaml` | Familiar for CI users |
| Keyword search baseline | `rank-bm25` | Pure Python, no server |
| Near-duplicate detection | MinHash LSH via `datasketch`; cosine on stored vectors when present | Scales past tens of thousands of chunks |
| HTML report | `jinja2` template, single self-contained file | No server, easy to attach to CI artifacts |
| Optional: embeddings | `sentence-transformers` (extra), or OpenAI-compatible HTTP endpoint | Covers local and hosted |
| Optional: Chroma | `chromadb` (extra) | First live connector |
| Optional: LLM for evalset | `litellm` (extra) | One interface for Ollama, OpenAI, Anthropic, others |
| Tests | `pytest`, `hypothesis` for text edge cases | |
| Lint/format/types | `ruff`, `mypy --strict` on `src/` | |

Install extras keep the base install light:

```
pip install ragcheckup                 # core checks, JSON/JSONL
pip install "ragcheckup[chroma]"       # + Chroma connector
pip install "ragcheckup[embed]"        # + sentence-transformers for exact-string check
pip install "ragcheckup[llm]"          # + litellm for evalset
pip install "ragcheckup[all]"
```

## 3. Repository layout

```
ragcheckup/
├── pyproject.toml
├── README.md
├── LICENSE                     # MIT (owner's decision)
├── NOTICE                      # credits, incl. ChunkLint's MIT notice if any code is copied
├── docs/
│   ├── PRD.md
│   ├── TECHNICAL_DESIGN.md
│   └── checks/<check-id>.md    # one page per check: what, why, fix, examples
├── src/ragcheckup/
│   ├── __init__.py             # public API: scan(), load(), Report
│   ├── cli.py
│   ├── config.py
│   ├── models.py               # Chunk, ChunkSet, Finding, CheckResult, Report
│   ├── normalize.py            # metadata key mapping
│   ├── engine.py
│   ├── connectors/
│   │   ├── base.py             # Connector protocol, URI parsing
│   │   ├── jsonfile.py         # .json / .jsonl
│   │   └── chroma.py
│   ├── retrieval/
│   │   ├── base.py             # Retriever protocol
│   │   ├── bm25.py
│   │   ├── vector.py           # uses connector's native query or local index
│   │   └── embedders.py        # sentence-transformers / HTTP / chroma-stored
│   ├── checks/
│   │   ├── base.py             # Check protocol, registry, decorator
│   │   ├── tables.py
│   │   ├── context.py
│   │   ├── versions.py
│   │   ├── hygiene.py
│   │   └── exact.py
│   ├── evalset/
│   │   ├── generate.py
│   │   └── export.py           # ragas, deepeval writers
│   ├── reporters/
│   │   ├── terminal.py
│   │   ├── jsonreport.py
│   │   └── html/ (report.py, template.html.j2)
│   └── textutil.py             # tokenization, sentence boundary helpers
├── corpus/                     # M0 planted test corpus
│   ├── docs/*.md               # ~30 source documents
│   ├── labels.yaml             # ground truth: which chunk/doc has which problem
│   ├── build.py                # chunk → chunks.jsonl, and load into Chroma
│   └── README.md               # what is planted and why (also the RAG tutorial)
├── benchmarks/
│   └── run.py                  # precision/recall per check against labels.yaml
└── tests/
    ├── unit/                   # one file per check module
    ├── integration/            # connectors, CLI end to end
    └── fixtures/               # small hand-made chunk files
```

## 4. Data model

```python
class Chunk(BaseModel):
    id: str                       # stable ID from source; synthesized "row-<n>" if absent (and flagged)
    text: str
    metadata: dict[str, Any]
    source: str | None            # normalized from metadata
    title: str | None             # normalized: title/heading/section/...
    position: int | None          # order within source, if known
    updated: datetime | None      # normalized from version/date keys
    vector: list[float] | None    # present when the connector exposes stored embeddings

class ChunkSet:
    chunks: list[Chunk]
    origin: str                   # URI scanned
    def by_source(self) -> dict[str, list[Chunk]]  # sorted by position
    stats: CorpusStats            # word-count distribution, numeric ratios, etc. computed once

class Finding(BaseModel):
    check_id: str                 # e.g. "context.dangling_reference"
    severity: Literal["high", "medium", "low"]
    chunk_ids: list[str]          # one or more (e.g. a duplicate pair)
    message: str                  # human sentence, specific to this finding
    evidence: dict[str, Any]      # numbers that triggered it (ratio, similarity, ...)
    fix_url: str                  # link to docs/checks/<id>.md on the docs site

class CheckResult(BaseModel):
    check_id: str
    failure_mode: Literal["tables", "context", "exact", "versions", "hygiene"]  # evalset is a separate command, never in scan results
    status: Literal["ran", "skipped", "error"]
    skipped_reason: str | None
    findings: list[Finding]
    summary: dict[str, Any]       # e.g. {"affected_share": 0.18} or miss rates

class Report(BaseModel):
    tool_version: str
    schema_version: int = 1
    origin: str
    chunk_count: int
    started_at: datetime
    duration_ms: int
    results: list[CheckResult]
    score_by_failure_mode: dict[str, int]   # 0–100, see section 8
```

The JSON report is `Report.model_dump_json()`. Its JSON Schema is generated from the
model and committed at `docs/report.schema.json`; a test fails if they drift.

## 5. Metadata normalization

Real indexes use inconsistent keys. `normalize.py` maps them with a configurable list:

| Field | Default keys tried, in order |
|---|---|
| `id` | `id`, `chunk_id`, `doc_id`, `_id`, `node_id` |
| `source` | `source`, `file_path`, `file_name`, `url`, `document_id`, `doc_id` |
| `title` | `title`, `heading`, `section`, `header`, `heading_path`, `document_title`, `h1`/`h2`/`h3` |
| `position` | `position`, `chunk_index`, `seq_num`, `page` + `start_index` |
| `updated` | `updated_at`, `last_modified`, `modified`, `date`, `version_date`, `effective_date` |
| `version` | `version`, `revision` |

LangChain and LlamaIndex default metadata shapes are covered by these lists. Users extend
them in config.

## 6. Connectors

```python
class Connector(Protocol):
    def load(self) -> ChunkSet: ...
    def native_retriever(self) -> Retriever | None: ...   # vector query using the DB itself
    def stored_embedder(self) -> Embedder | None: ...     # the model the index was built with, if discoverable
```

Sources are addressed by URI:

| URI | Connector |
|---|---|
| `path/to/chunks.jsonl`, `path/to/chunks.json` | JSON file. Accepts a list of objects or JSONL. Text key `text`, `page_content` or `content`; metadata key `metadata` or remaining fields. |
| `chroma://<persist_dir>/<collection>` | Chroma persistent client |
| `chroma+http://host:port/<collection>` | Chroma HTTP client |

**Chroma details.** Load with `collection.get(include=["documents", "metadatas", "embeddings"])`
in pages of 1,000 to bound memory. `native_retriever()` uses `collection.query(query_embeddings=...)`.
`stored_embedder()` returns the collection's configured embedding function when Chroma
persists it (newer Chroma versions record the embedding function configuration on the
collection); the builder must verify the exact API on the Chroma version pinned at build
time. If no embedding function is discoverable, return `None`; the exact-string check then
requires `--embed-model`. The corpus demo collections are created with an explicit
embedding function so that discovery works in the demo, and the README demo command also
passes `--embed-model` so it works regardless of Chroma version.

**Read-only guarantee.** Connectors only call read methods. An integration test wraps the
client and fails on any write call.

**Scale target for v1:** 100,000 chunks on a laptop with 16 GB RAM in under 5 minutes
for the structural checks (no embeddings), single process. Simplicity wins over speed in
0.1.0 because the owner must be able to read every line **(drafter's call)**.

## 7. Checks

### 7.1 Check framework

```python
@register(id="context.dangling_reference", failure_mode="context", default_severity="medium",
          scope="chunk")   # "chunk" | "corpus" | "retrieval"
def dangling_reference(chunk: Chunk, ctx: CheckContext) -> Iterable[Finding]: ...
```

- **chunk** scope: called per chunk (run sequentially in 0.1.0).
- **corpus** scope: receives the whole `ChunkSet` (duplicates, versions, size outliers).
- **retrieval** scope: receives `ChunkSet` plus a `RetrievalContext` (BM25 index, vector
  retriever). Skipped with a reason if requirements are missing.

`CheckContext` carries config, corpus stats and helper functions. All thresholds come from
config with defaults defined next to each check. Each check has a docs page under
`docs/checks/` and a unit test file.

### 7.2 Tables (failure 1)

- **`table.flattened_numeric`** — tokenize; compute `numeric_ratio = numeric_tokens / all_tokens`
  and `label_density` = share of numeric tokens with an alphabetic token within a window of
  2. Flag when `numeric_ratio ≥ 0.4` and `label_density < 0.3` and the chunk has at least
  12 numeric tokens. Numbers are tuned on the corpus (M2) and stored as defaults.
  Excludes code blocks and chunks whose metadata marks them as tables already
  serialized row-wise.
- **`table.markdown_broken`** — parse pipe tables: flag inconsistent column counts across
  rows, a missing `|---|` separator after the header, or a header with zero data rows.
- **`table.header_orphan`** — a run of 3+ short title-cased tokens on one line, followed by
  no line containing the same column count of values, at the end of a chunk.

### 7.3 Context (failure 2)

- **`context.missing_heading`** — no normalized `title`, and none of the first 2 lines
  look like a heading (markdown `#`, all-caps line, or short line followed by a blank line).
- **`context.dangling_reference`** — first sentence starts with a demonstrative or pronoun
  from a configurable list (`this`, `that`, `these`, `those`, `it`, `they`, `the above`,
  `as mentioned`, `as noted`, `the following`) and the referent noun phrase is not
  present in the same chunk's title. Own word list, not copied from other tools.
- **`context.starts_mid_sentence`** — first character lowercase (excluding an allowlist of
  identifiers that are legitimately lowercase, such as `iPhone`, `npm`, `macOS`), or first
  word is a coordinating or subordinating conjunction.
- **`context.ends_mid_sentence`** — last non-space character is not terminal punctuation,
  closing bracket or a colon; raised to `high` when the next chunk of the same source
  (by `position`) starts lowercase, which indicates a confirmed split.
- **`context.size_outlier`** — word counts outside `[P5 / 2, P95 × 2]` of this index's own
  distribution, plus absolute floor (fewer than 8 words) and ceiling (over 1,500 words).
  Relative thresholds avoid flooding indexes that chose a different chunk size on purpose.

### 7.4 Exact-string blind spot (failure 3)

**Goal.** Measure how often the chunk containing an exact identifier is missing from the
top-k results when you search for that identifier, for vector search versus keyword
search.

**Step 1 — identifier extraction** (`exact.py`):

| Family | Pattern idea |
|---|---|
| Error/status codes | `[A-Z]{2,6}-?\d{2,6}` (e.g. `ERR-4012`, `E1043`), HTTP-style `\b[45]\d{2}\b` only when preceded by "error"/"status" |
| SKUs / part numbers | mixed letter-digit tokens of length 5–20 containing both, optionally with `-` or `/` |
| Ticket IDs | `[A-Z][A-Z0-9]+-\d+` (Jira style), `#\d{3,}` |
| Version strings | `v?\d+\.\d+(\.\d+)?` |
| Proper names | capitalized multi-word spans not at sentence start, appearing in 1–5 chunks |

Keep identifiers that appear in between 1 and 5 chunks (rare enough to be specific),
deduplicate, sample up to 300 (configurable) with a fixed seed so runs are reproducible.

**Step 2 — retrieval.** For each identifier, build the query as the bare identifier and a
short templated question ("What is ERR-4012?"). Run:

- **Keyword baseline:** BM25 over all chunk texts (`rank-bm25`, built in memory).
- **Vector:** embed the query with the index's model and use the connector's
  `native_retriever()` if available, else cosine similarity over stored vectors, else
  over vectors computed locally (only when the user explicitly passes `--embed-model` and
  accepts the cost of embedding the corpus).

**Step 3 — metric.** `hit@k` (default k = 5): whether any chunk containing the identifier
appears in the top k. Report vector miss rate, BM25 miss rate, and the list of identifiers
that vector search missed but BM25 found.

**Embedding model resolution, in order:**

1. `connector.stored_embedder()` (for Chroma, the collection's recorded embedding function).
2. `--embed-model` flag: a sentence-transformers model name, or `openai:<model>` /
   `http://...` for an OpenAI-compatible endpoint (API key from environment).
3. None: the check is **skipped** with the message "Exact-string check needs the
   embedding model used to build this index. Pass --embed-model."

Safety: if the query embedding dimension differs from stored vectors, fail the check with
a clear error. If the model is user-supplied rather than discovered, print a warning that
results are only valid if it matches the index's model. Any hosted embedding call prints
the estimated number of calls and requires `--yes` in non-interactive mode.

**Severity.** `high` when vector miss rate exceeds BM25 miss rate by 30 points or more;
`medium` at 15 points; otherwise informational.

### 7.5 Versions and hygiene (failure 4)

- **`hygiene.exact_duplicate`** — hash of normalized text (lowercased, whitespace
  collapsed). Groups of 2+.
- **`version.near_duplicate`** — candidate pairs from MinHash LSH (5-word shingles, 128
  permutations, Jaccard threshold 0.8). If stored vectors exist, confirm with cosine ≥ 0.95.
  Report only pairs with **different `source`** or different `updated`/`version`; pairs
  from the same source are reported separately as low-severity overlap.
- **`version.same_title_multiple_dates`** — group by normalized title (and by source file
  stem with year/version tokens stripped, e.g. `leave-policy-2023.pdf` and
  `leave_policy_2025.pdf`); flag groups with more than one distinct date or version.
  Severity `high` when the groups also contain near-duplicate chunks.
- **`version.missing_freshness_metadata`** — corpus-level: share of chunks with no
  `updated` or `version`. One finding, not one per chunk.
- **`hygiene.missing_id_or_source`** — chunks without a real ID or source.
- **`hygiene.empty_or_noise`** — empty text; lines repeated across more than 30% of
  chunks of one source (page headers/footers); line-break ratio above 0.35.

### 7.6 Evaluation set generation (failure 5, M6)

1. Stratified sample of chunks (by source), default 50.
2. For each, ask the LLM (via `litellm`) for one question answerable only from that chunk
   plus a short reference answer. Prompt asks for JSON; invalid output is retried once
   then dropped.
3. Run retrieval for each question; record hit@k for the source chunk.
4. Write `evalset/questions.jsonl` (ragcheckup's own format) plus exporters for ragas and
   deepeval. **Both libraries have changed their dataset APIs recently; the builder must
   check the current dataset schema of each at build time and pin tested versions**
   rather than relying on field names written here.

The command is opt-in and prints the number of LLM calls before running.

## 8. Scoring

Each failure mode gets a 0–100 score, mainly to make the summary scannable:

- Structural modes (tables, context, versions, hygiene):
  `100 × (1 − weighted_affected_share)` where affected chunks are weighted by severity
  (high 1.0, medium 0.5, low 0.1), with a floor of 0.
- Exact mode: `100 − max(0, vector_miss_rate − bm25_miss_rate)` in percentage points.
  The terminal and HTML summaries always print both raw miss rates next to the score;
  the raw vector miss rate is the headline number in messages, the gap drives score and
  severity.
- Modes whose checks were skipped show "not run", never 100.
- There are exactly five scored groups: tables, context, exact, versions, hygiene. The
  `evalset` command is not scored.

Scores are secondary. The findings list is the product.

## 9. Configuration

`ragcheckup.yaml` in the working directory, or `--config path`:

```yaml
version: 1
fail_on: high            # high | medium | low | never
metadata_keys:
  title: [title, heading, section]
  updated: [updated_at, effective_date]
checks:
  context.dangling_reference:
    severity: low
  table.flattened_numeric:
    numeric_ratio: 0.45
  exact.vector_miss_rate:
    k: 5
    sample: 300
disable:
  - context.size_outlier
ignore:
  chunk_ids: [faq-001]
  sources: ["legacy/*"]
```

Inline suppression for exported files: a chunk with `metadata.ragcheckup_ignore: [check-id]`
is skipped for those checks.

## 10. CLI

```
ragcheckup scan SOURCE [--config PATH] [--format terminal|json|html] [--output PATH]
                       [--fail-on high|medium|low|never] [--checks ID,...] [--skip ID,...]
                       [--embed-model NAME] [--k N] [--sample N] [--seed N]
                       [--yes] [--verbose] [--quiet]
ragcheckup checks                  # list checks with IDs, failure mode, needs, default severity
ragcheckup explain CHECK_ID        # print the docs page for a check
ragcheckup evalset SOURCE --llm MODEL --embed-model NAME --out DIR [--n 50]
ragcheckup version
```

Exit codes: `0` no findings at or above `--fail-on`; `1` findings at or above it; `2`
usage or configuration error; `3` source could not be read.

## 11. Reporters

- **Terminal:** summary table (failure mode, score, finding counts by severity), then top
  10 findings by severity with chunk ID, one-line message and fix link. `--verbose` lists
  all. Chunk text excerpts are truncated to 160 characters.
- **JSON:** the full `Report` (section 4). Stable schema, versioned.
- **HTML:** single file, no external assets, sortable findings table, filter by check,
  expandable chunk text, the summary scores at the top. Must render offline.

## 12. Performance

- Single process in 0.1.0. A process pool for chunk-scope checks is a later optimization
  if the 5-minute target is missed.
- Corpus stats computed once and shared.
- MinHash keeps near-duplicate detection roughly linear.
- Retrieval checks are bounded by `--sample` (default 300 queries).
- Benchmark target in section 6; a `benchmarks/perf.py` script generates synthetic
  100k-chunk files for regression timing.

## 13. Testing strategy

Development is test-first per check: write the failing unit test from a fixture, then
implement.

| Layer | What | Where |
|---|---|---|
| Unit | Each check: positive cases, negative cases, edge cases (unicode, empty, very long, code blocks). `hypothesis` for tokenizer and sentence-boundary helpers. | `tests/unit/test_<module>.py` |
| Fixtures | Small hand-written chunk files, one per check, each with expected findings in a sidecar `expected.yaml` | `tests/fixtures/` |
| Golden corpus | The M0 planted corpus. `benchmarks/run.py` computes precision and recall per check against `corpus/labels.yaml`. CI fails if any high-severity check drops below its target (PRD section 12) or if the clean control set exceeds 5% flagged. | `corpus/`, `benchmarks/` |
| Integration | JSONL and Chroma connectors return identical `ChunkSet`s for the same corpus; read-only guard; CLI end to end with exit codes; JSON report validates against the committed schema. | `tests/integration/` |
| Snapshot | Terminal and HTML output for the corpus compared against stored snapshots (updated deliberately). | `tests/integration/snapshots/` |
| Optional | Exact-string and evalset tests run with a tiny local sentence-transformers model, marked `@pytest.mark.slow`; LLM calls mocked in normal runs. | |

CI (GitHub Actions): `ruff`, `mypy`, unit + integration tests on Python 3.10–3.13, the
benchmark gate for structural checks (no model needed), and a build of the wheel. Slow
tests, including the exact-string benchmark gate, run nightly with the pinned corpus
embedding model cached.

## 14. The planted corpus (M0) in detail

- **Company:** fictional ("Northwind Gear", an outdoor equipment retailer) **(drafter's call)**.
- **~30 Markdown documents:** return policy (2023 and 2025 versions), leave policy (two
  versions), product catalogue pages with SKUs, troubleshooting guides with error codes,
  support runbooks with ticket IDs, quarterly metrics with tables, and an FAQ.
- **Planted problems** (each labeled in `labels.yaml` with document, chunk and check ID):
  flattened tables, headings separated from content, sentences split across chunks,
  pronoun-led chunks, version pairs, repeated page footers, empty chunks, chunks missing
  metadata. About one third of the documents are a clean control set.
- **`build.py`** chunks the documents two ways — a "naive" splitter (fixed size, no
  headings, which plants failures realistically) and a "good" splitter (heading-aware,
  table rows serialized with headers) — and writes `chunks_naive.jsonl`,
  `chunks_good.jsonl` and two Chroma collections. The naive vs good contrast is the demo:
  the naive index fails loudly, the good index is mostly clean.
- **`corpus/README.md`** explains each planted problem in plain language. It doubles as the
  owner's RAG tutorial.

**Pinned corpus embedding model.** Both Chroma collections are built with
`sentence-transformers/all-MiniLM-L6-v2` (Apache-2.0, small, CPU-friendly) at a pinned
version **(drafter's call)**. The same model is used by the exact-string tests.

**Label format.** Labels are tied to **text spans in the source documents**, not to chunk
IDs, so they survive both splitters:

```yaml
- id: L014
  doc: docs/returns-policy-2023.md
  anchor: "Q3 refund rate"        # verbatim string that appears in the problem region
  check: table.flattened_numeric
  applies_to: [naive]             # which index(es) should exhibit it
- id: L031
  doc: docs/error-codes.md
  identifier: ERR-4012            # planted identifiers for the exact-string check
  check: exact.vector_miss_rate
```

**Precision and recall rules** (`benchmarks/run.py`):

- Unit of measurement is the **planted problem** (one label).
- A label is *found* when at least one finding from its check ID references a chunk whose
  text contains the anchor (for corpus-level findings with several chunk IDs, any of them).
- **Recall** per check = found labels / labels for that check, measured on the index(es)
  in `applies_to` (the naive index for most).
- **Precision** per check = findings that match some label / all findings from that check,
  measured on the naive index.
- **False-positive rate** = share of chunks from clean-control documents flagged at any
  severity, measured on **both** indexes, target at most 5%.
- For `exact.vector_miss_rate`, the gated numbers are identifier extraction recall
  (planted identifiers found by extraction, target at least 0.9) and the reported gap on
  the naive index (target at least 15 points). This runs in the nightly slow job and in
  local runs, because it needs the embedding model.

## 15. Security and privacy

- No telemetry. No network calls unless the user passes a hosted embedding or LLM option.
- Reports can contain chunk text; the README warns not to publish reports from private
  indexes, and `--redact` replaces chunk excerpts with hashes.
- API keys only read from environment variables, never written to reports or logs.
- Connectors are read-only (section 6).

## 16. Release and versioning

- Semantic versioning. Check IDs are stable API; renaming one is a breaking change.
- Report `schema_version` bumps on breaking JSON changes.
- Release via GitHub Actions to PyPI with trusted publishing on tag `v*`.
- 0.1.0 = PRD milestones M0–M5. 0.2.0 = M6 + Qdrant.

## 17. Open items left to the builder

- Exact default thresholds for table and context checks: start with the values above, tune
  on the corpus in M1–M2, record final numbers in each check's docs page.
- Choice of the tiny embedding model used in tests (any small sentence-transformers model
  with a permissive license).
- HTML report visual design.
- Whether to add a `--diff` mode comparing two reports (useful for CI, not required for
  0.1.0).
