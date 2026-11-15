# Northwind Gear — Planted Test Corpus

This corpus simulates a fictional outdoor equipment retailer ("Northwind Gear") and is used for:

1. **Testing every check** in ragcheckup against known ground truth.
2. **Demonstrating the tool** in README, documentation, and launch materials.
3. **Learning** — building this corpus is the owner's hands-on introduction to how RAG indexes fail.

## Company

**Northwind Gear** sells outdoor equipment (tents, backpacks, stoves, clothing) and provides internal policies for employees and support documentation for customers.

## Documents (30 total)

### Policies (internal HR) — ~15 docs, ~half "clean"

| # | Document | Description | Problems Planted? |
|---|---|---|---|
| 1 | `returns-policy-2023.md` | Return/refund policy, 2023 version | ✅ Yes |
| 2 | `returns-policy-2025.md` | Return/refund policy, 2025 version | ✅ Yes (conflicts with 2023) |
| 3 | `leave-policy-2023.md` | PTO/sick leave policy, 2023 | ✅ Yes |
| 4 | `leave-policy-2025.md` | PTO/sick leave policy, 2025 | ✅ Yes (conflicts with 2023) |
| 5 | `remote-work-policy.md` | Remote work guidelines | ✅ Yes (dangling refs, mid-sentence chunks) |
| 6 | `code-of-conduct.md` | Workplace conduct rules | ✅ Yes (orphan headers) |
| 7 | `travel-policy.md` | Business travel guidelines | ✅ Yes (flattened tables) |
| 8 | `it-security-policy.md` | IT security & access rules | ✅ Yes (missing headings) |
| 9 | `health-benefits.md` | Employee health benefits guide | ✅ Yes (version conflicts) |
| 10 | `recruitment-guide.md` | Hiring process for open roles | ✅ Yes |
| 11 | `expense-reimbursement.md` | Employee expense policy | ✅ Yes (flattened tables) |
| 12 | `dress-code.md` | Workplace dress code | ✅ Yes |
| 13 | `parking-policy.md` | Employee parking rules | ✅ Yes |
| 14 | `emergency-procedures.md` | Building emergency procedures | ✅ Yes (dangling refs) |
| 15 | `training-calendar.md` | Annual training schedule | ✅ Yes (version dates) |

### Product Catalog (customer-facing) — ~8 docs

| # | Document | Description | Problems Planted? |
|---|---|---|---|
| 16 | `product-tents.md` | Tent catalogue with SKUs | ✅ Yes (SKUs, broken tables) |
| 17 | `product-backpacks.md` | Backpack catalogue with SKUs | ✅ Yes (SKUs, broken tables) |
| 18 | `product-stoves.md` | Camping stove catalogue | ✅ Yes (error codes, SKUs) |
| 19 | `product-clothing.md` | Clothing catalogue | ✅ Yes (missing headings) |
| 20 | `product-accessories.md` | Accessories (headlamps, etc.) | ✅ Yes |
| 21 | `product-boats.md` | Inflatable boats catalogue | ✅ Yes |
| 22 | `product-sale-2024.md` | Seasonal sale catalogue | ✅ Yes (version conflict with regular) |
| 23 | `product-sale-2025.md` | Seasonal sale catalogue | ✅ Yes (version conflict) |

### Troubleshooting & Support — ~5 docs

| # | Document | Description | Problems Planted? |
|---|---|---|---|
| 24 | `troubleshooting-stoves.md` | Stove troubleshooting with error codes | ✅ Yes (error codes, exact strings) |
| 25 | `troubleshooting-tents.md` | Tent troubleshooting | ✅ Yes (mid-sentence chunks) |
| 26 | `faq.md` | Frequently asked questions | ✅ Yes (dangling refs, orphans) |
| 27 | `warranty-policy.md` | Product warranty terms | ✅ Yes (version dates, missing headings) |
| 28 | `shipping-guidelines.md` | Shipping & delivery info | ✅ Yes (empty chunks, noise) |

### Support Runbooks (internal) — ~2 docs

| # | Document | Description | Problems Planted? |
|---|---|---|---|
| 29 | `support-runbook-1.md` | Tier-1 support runbook (ticket IDs) | ✅ Yes |
| 30 | `support-runbook-2.md` | Tier-2 support runbook (ticket IDs) | ✅ Yes |

### Clean Control Set (no planted problems) — ~5 docs

These documents have **no planted problems** and are used to verify the false-positive rate stays below 5%:

| # | Document | Description |
|---|---|---|
| 31 | `about-us.md` | Company history and mission |
| 32 | `customer-service-contacts.md` | Contact information (phone, email, chat) |
| 33 | `store-locations.md` | Retail store addresses and hours |
| 34 | `gift-cards.md` | Gift card terms and conditions |
| 35 | `loyalty-program.md` | Loyalty program rules |

---

## Planted Problems Summary

| Problem Type | What | Affected Docs |
|---|---|---|
| **Flattened tables** | PDF tables parsed into streams of numbers with no headers | `travel-policy`, `expense-reimbursement`, `product-tents`, `product-backpacks` |
| **Broken Markdown tables** | Inconsistent column counts, missing separators | `product-tents`, `product-backpacks` |
| **Orphan headers** | Title-cased lines at chunk end with no data following | `code-of-conduct`, `faq` |
| **Missing headings** | Chunks with no title in metadata AND no heading-like text | `it-security-policy`, `product-clothing`, `warranty-policy` |
| **Dangling references** | Chunks opening with "this", "these", "the following" | `remote-work-policy`, `faq`, `emergency-procedures`, `loyalty-program` |
| **Mid-sentence chunks** | Chunks beginning with lowercase or connectors | `remote-work-policy`, `troubleshooting-tents`, `troubleshooting-stoves` |
| **Ends mid-sentence** | Chunks ending without terminal punctuation | Several context-affected docs |
| **Version conflicts** | Same document title with different dates (2023 vs 2025) | `returns-policy-2023.md` + `returns-policy-2025.md`, `leave-policy-2023.md` + `leave-policy-2025.md`, `product-sale-2024.md` + `product-sale-2025.md` |
| **Missing freshness metadata** | Chunks with no date/version | Several (all docs without updated metadata) |
| **Exact strings / SKUs** | Product codes, error codes, ticket IDs used throughout | `product-*`, `troubleshooting-*`, `support-runbook-*` |
| **Empty chunks** | Empty text chunks | `shipping-guidelines`, `faq` |
| **Noise / repeated footers** | Repeated page headers across many chunks | `shipping-guidelines` |
| **Missing IDs / sources** | Chunks without stable ID or source reference | Some chunks in support runbooks, FAQ |

## Labels

Ground truth for every planted problem is tracked in **`labels.yaml`** (see separate file). Each label has:

```yaml
- id: L001
  doc: docs/returns-policy-2023.md
  anchor: "Q3 refund rate"          # verbatim string in the problem region
  check: table.flattened_numeric    # which check should flag it
  applies_to: [naive]               # which index: naive or good
```

## Index Builds

The corpus is split two ways by **`build.py`**:

1. **"Naive" index** — fixed-size chunks (300 words, no heading awareness). Plants failures realistically.
2. **"Good" index** — heading-aware splitting (respects markdown headings, table boundaries). Mostly clean.

The naive vs good contrast is the demo: the naive index fails loudly, the good index is mostly clean.

### Output files

- `chunks_naive.jsonl` — chunks from naive splitter
- `chunks_good.jsonl` — chunks from good splitter
- `chroma_naive/` — Chroma collection from naive index
- `chroma_good/` — Chroma collection from good index

## Pinned Embedding Model

Both Chroma collections are built with **`sentence-transformers/all-MiniLM-L6-v2`** (384-dim vectors). This is the same model recommended for the exact-string check (`--embed-model all-MiniLM-L6-v2`).
