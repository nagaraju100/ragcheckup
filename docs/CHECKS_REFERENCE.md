# Checks Reference

Complete reference of all 15 checks in ragcheckup, organized by failure mode.
Each check runs on individual chunks (where noted) and the findings are
aggregated into a corpus-wide report.

## How to read this table

| Column | Meaning |
|---|---|
| **Check ID** | The unique identifier used in CLI flags (`--checks`, `--skip`) |
| **Scope** | `chunk` = runs on every individual chunk; `corpus` = runs on the full index |
| **Severity** | `high` = blocks retrieval, `medium` = degrades quality, `low` = worth knowing |

---

## 1. Tables (3 checks)

Checks whether chunked documents contain broken Markdown tables — a very
common silent failure when documents are split by naive chunkers.

| Check ID | Scope | Severity | What it detects |
|---|---|---|---|
| `table.markdown_broken` | chunk | **high** | Markdown tables missing the separator row (`|---|`), with inconsistent column counts (rows have different numbers of columns), or headers with no data rows. |
| `table.flattened_numeric` | chunk | **high** | Chunks dominated by numeric tokens with few labels — typical output from PDF table extraction where column structure is lost and data is "flattened" into a stream of numbers. |
| `table.header_orphan` | chunk | **medium** | A header-like line (e.g. `## Pricing`) at the end of a chunk with no table data following it in the same chunk — the table was split and the data landed in the next chunk. |

**Why it matters:** A user searching for a price or spec from a table will get nothing if the table is structurally broken, even if the surrounding text is fine.

---

## 2. Context (5 checks)

Checks whether chunks are split at sensible boundaries or whether
important context was lost during chunking.

| Check ID | Scope | Severity | What it detects |
|---|---|---|---|
| `context.starts_mid_sentence` | chunk | **high** | A chunk begins with a connector word (e.g. "For", "After", "Additionally") or lowercase word, suggesting it was split from a previous chunk — the beginning sentence is missing. |
| `context.ends_mid_sentence` | chunk | **medium** | A chunk ends without terminal punctuation (no period, exclamation, or question mark), suggesting the next chunk continues the thought — the ending was cut off. |
| `context.dangling_reference` | chunk | **medium** | A chunk opens with a pronoun ("it", "this", "they") or reference ("above", "the section") that points to information outside the chunk — the reference cannot be resolved within the chunk alone. |
| `context.missing_heading` | chunk | **medium** | A chunk has neither a title in its metadata nor a heading-like line (Markdown `#`, `##`) in its text — the system has no way to categorize or title this chunk. |
| `context.size_outlier` | corpus | **low** | Chunks whose word count falls far outside the index's distribution (below the 5th percentile or above the 95th percentile). Very small chunks carry little retrieval signal; very large chunks dilute specificity. |

**Why it matters:** Context problems mean chunks are split in wrong places — the content may exist, but the chunk is too disconnected from its surroundings to be useful for retrieval.

---

## 3. Exact (1 check)

The only corpus-level check that compares two retrieval methods side by side.

| Check ID | Scope | Severity | What it detects |
|---|---|---|---|
| `exact.vector_miss_rate` | corpus | **high** | Extracts identifiers (SKUs, error codes, ticket IDs, version strings) from the corpus, then runs both BM25 (keyword) and vector search against each one. Reports how often each method **misses** — and the gap between them. Pass `--embed-model all-MiniLM-L6-v2` to enable. |

**Example output:**
> "Vector search missed 56% of 582 exact-identifier lookups (keyword search missed 77%). Your users' code and SKU searches will fail. Enable hybrid search."

**Why it matters:** Tells you exactly how much value (or not) your vector search adds over keyword search for finding specific identifiers — the single most important metric for "is my vector index actually helping?"

---

## 4. Versions (3 checks)

Checks whether your index serves the most up-to-date content, or if stale
versions are mixed in with current ones.

| Check ID | Scope | Severity | What it detects |
|---|---|---|---|
| `version.missing_freshness` | corpus | **low** | Reports the percentage of chunks that have **no version, date, or last-updated metadata**. Without freshness info, the system cannot serve the most recent content. |
| `version.near_duplicate` | corpus | **medium** | Flags near-identical chunks (content-wise) from different sources or different dates — e.g., "IT Policy 2023" and "IT Policy 2025" have overlapping text. Users may retrieve the old version. |
| `version.same_title_multiple_dates` | corpus | **medium** | Flags groups of chunks with the same title but different version/date metadata — e.g., 4 chunks from "returns-policy" spanning 2023 and 2025. |

**Why it matters:** If a user asks about the "current leave policy" and the system returns the 2023 version alongside the 2025 version, the answer will be wrong.

---

## 5. Hygiene (3 checks)

Checks whether the index is clean, or whether garbage entries are wasting space
and confusing retrieval systems.

| Check ID | Scope | Severity | What it detects |
|---|---|---|---|
| `hygiene.exact_duplicate` | corpus | **medium** | Flags byte-identical chunk text appearing more than once in the index — e.g., `leave-policy-2023.md_chunk2_good` and `leave-policy-2025.md_chunk2_good` have the exact same text. This wastes index space and may confuse ranking. |
| `hygiene.missing_id_or_source` | corpus | **medium** | Flags chunks with no stable ID or no source file reference — the system cannot trace where the chunk came from. |
| `hygiene.empty_or_noise` | corpus | **high** | Flags empty chunks (zero words) and chunks with excessive noise (high line-break ratio suggesting repeated page headers, footers, or PDF extraction artifacts). |

**Why it matters:** Empty and duplicate chunks waste storage and confuse ranking algorithms. Noise chunks (page headers, repeated disclaimers) pollute every search result.

---

## Summary by severity

| Severity | Count | Action |
|---|---|---|
| **High** | 6 | Blocks retrieval entirely — fix immediately |
| **Medium** | 7 | Degrades quality — should fix soon |
| **Low** | 2 | Worth knowing about — fix when convenient |

---

## Quick reference: run specific checks

```bash
# Run only the exact-string check
ragcheckup scan chunks.jsonl --checks exact.vector_miss_rate

# Run only table checks
ragcheckup scan chunks.jsonl --checks table.markdown_broken,table.flattened_numeric

# Skip noise-heavy checks
ragcheckup scan chunks.jsonl --skip hygiene.empty_or_noise
```
