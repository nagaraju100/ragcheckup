"""Context checks (Failure 2) — lost context, mid-sentence chunks, size outliers."""

from __future__ import annotations

from ragcheckup.checks.base import CheckContext, register, _default_severity
from ragcheckup.models import Chunk, ChunkSet, Finding, Severity
from ragcheckup.textutil import (
    CONNECTIVES,
    DANGLING_STARTERS,
    ALLOWED_LOWERCASE,
    count_tokens,
    is_sentence_start,
    looks_like_heading,
    line_break_ratio,
    sentence_count,
)


# ---------------------------------------------------------------------------
# Chunk-scope checks
# ---------------------------------------------------------------------------

@register(
    id="context.missing_heading",
    failure_mode="context",
    default_severity="medium",
    scope="chunk",
)
def missing_heading(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag chunks with no title in metadata AND no heading-like text."""
    if chunk.title:
        return []
    # Check if the first lines look like a heading
    first_lines = chunk.text.strip().splitlines()[:2]
    if any(looks_like_heading(line) for line in first_lines):
        return []
    return [
        Finding(
            check_id="context.missing_heading",
            severity=_default_severity("medium"),
            chunk_ids=[chunk.id],
            message=(
                f"Chunk {chunk.id} has no heading or title. "
                f"Users cannot tell what this chunk is about without scanning it."
            ),
            evidence={"has_title": False, "has_heading_text": False},
            fix_url=f"/checks/context.missing_heading.html",
        )
    ]


@register(
    id="context.dangling_reference",
    failure_mode="context",
    default_severity="medium",
    scope="chunk",
)
def dangling_reference(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag chunks that open with a pronoun referring to something outside the chunk."""
    text = chunk.text.strip()
    first_sentence = text.split(".")[0].split(";")[0].split(":")[0].strip()

    for starter in DANGLING_STARTERS:
        if first_sentence.lower().startswith(starter):
            # Check if the referent noun phrase is in the title
            title_lower = (chunk.title or "").lower()
            # Extract potential referent from the phrase
            referent_found = False
            if "this" in starter.lower() or "these" in starter.lower():
                referent_found = chunk.title and any(
                    word for word in chunk.title.lower().split() if word not in ("a", "the", "is")
                )
            elif "it" in starter.lower() or "its" in starter.lower():
                referent_found = bool(chunk.title)

            if not referent_found:
                return [
                    Finding(
                        check_id="context.dangling_reference",
                        severity=_default_severity("medium"),
                        chunk_ids=[chunk.id],
                        message=(
                            f"Chunk {chunk.id} opens with a dangling reference "
                            f"('{first_sentence[:60]}...'). The referent is not "
                            f"stated in the same chunk."
                        ),
                        evidence={"starter": starter, "first_sentence": first_sentence[:100]},
                        fix_url=f"/checks/context.dangling_reference.html",
                    )
                ]
    return []


@register(
    id="context.starts_mid_sentence",
    failure_mode="context",
    default_severity="high",
    scope="chunk",
)
def starts_mid_sentence(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag chunks beginning with a lowercase word (not an allowlist) or a connector."""
    text = chunk.text.strip()
    if not text:
        return []

    first_word = text[0]

    # Starts with a coordinating/subordinating conjunction
    words = text.split()
    if words and words[0].lower() in CONNECTIVES:
        return [
            Finding(
                check_id="context.starts_mid_sentence",
                severity=_default_severity("high"),
                chunk_ids=[chunk.id],
                message=(
                    f"Chunk {chunk.id} starts with a connector word "
                    f"('{words[0]}'). This chunk likely belongs to a previous one."
                ),
                evidence={"first_word": words[0]},
                fix_url=f"/checks/context.starts_mid_sentence.html",
            )
        ]

    # Starts with a lowercase word (unless it's an allowed lowercase identifier)
    if first_word.isalpha() and first_word.islower():
        if words[0].lower() not in ALLOWED_LOWERCASE:
            return [
                Finding(
                    check_id="context.starts_mid_sentence",
                    severity=_default_severity("high"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} starts with a lowercase word "
                        f"('{first_word}'). This indicates the chunk was split "
                        f"in the middle of a sentence."
                    ),
                    evidence={"first_char": first_word},
                    fix_url=f"/checks/context.starts_mid_sentence.html",
                )
            ]

    return []


@register(
    id="context.ends_mid_sentence",
    failure_mode="context",
    default_severity="medium",
    scope="chunk",
)
def ends_mid_sentence(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag chunks ending without terminal punctuation."""
    text = chunk.text.strip()
    if not text:
        return []

    last_char = text.rstrip()[-1] if text.rstrip() else ""
    terminal = {".", "!", "?", ")", "}", "]", '"', "'"}

    if last_char not in terminal:
        # Check if next chunk of same source starts lowercase (confirmation for high)
        return [
            Finding(
                check_id="context.ends_mid_sentence",
                severity=_default_severity("medium"),
                chunk_ids=[chunk.id],
                message=(
                    f"Chunk {chunk.id} ends without terminal punctuation. "
                    f"It may be split from the next chunk."
                ),
                evidence={"last_char": last_char, "truncated_text": text[-80:]},
                fix_url=f"/checks/context.ends_mid_sentence.html",
            )
        ]

    return []


# ---------------------------------------------------------------------------
# Corpus-scope checks
# ---------------------------------------------------------------------------

@register(
    id="context.size_outlier",
    failure_mode="context",
    default_severity="low",
    scope="corpus",
)
def size_outlier(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag chunks whose word count is far from the index's distribution."""
    stats = ctx.stats
    if stats.total_chunks < 10:
        return []  # Need enough chunks for meaningful percentiles

    findings: list[Finding] = []

    for chunk in chunks:
        wc = chunk.word_count

        # Absolute floor and ceiling
        if wc < 8:
            findings.append(
                Finding(
                    check_id="context.size_outlier",
                    severity=_default_severity("low"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} has only {wc} words. "
                        f"Chunks with very few words carry little retrieval signal."
                    ),
                    evidence={"word_count": wc, "floor": 8},
                    fix_url=f"/checks/context.size_outlier.html",
                )
            )
        elif wc > 1500:
            findings.append(
                Finding(
                    check_id="context.size_outlier",
                    severity=_default_severity("low"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} has {wc} words. "
                        f"Very large chunks dilute the embedding with unrelated content."
                    ),
                    evidence={"word_count": wc, "ceiling": 1500},
                    fix_url=f"/checks/context.size_outlier.html",
                )
            )
        else:
            # Relative check: outside [P5/2, P95*2]
            p5 = stats.word_count_p5
            p95 = stats.word_count_p95
            if p5 > 0 and wc < (p5 / 2):
                findings.append(
                    Finding(
                        check_id="context.size_outlier",
                        severity=_default_severity("low"),
                        chunk_ids=[chunk.id],
                        message=(
                            f"Chunk {chunk.id} has {wc} words, well below this index's "
                            f"distribution (P5≈{p5:.0f})."
                        ),
                        evidence={
                            "word_count": wc,
                            "p5": p5,
                            "threshold": p5 / 2,
                        },
                        fix_url=f"/checks/context.size_outlier.html",
                    )
                )
            elif p95 > 0 and wc > (p95 * 2):
                findings.append(
                    Finding(
                        check_id="context.size_outlier",
                        severity=_default_severity("low"),
                        chunk_ids=[chunk.id],
                        message=(
                            f"Chunk {chunk.id} has {wc} words, well above this index's "
                            f"distribution (P95≈{p95:.0f})."
                        ),
                        evidence={
                            "word_count": wc,
                            "p95": p95,
                            "threshold": p95 * 2,
                        },
                        fix_url=f"/checks/context.size_outlier.html",
                    )
                )

    return findings

