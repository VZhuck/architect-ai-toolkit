# Mine One File

Brief for mining NFRs from **one** source file. It runs in a subagent (one per file) or inline in the main thread. It never asks the user anything: when unsure, make the conservative choice, write the reason in `Interpretation`, and move on.

## Inputs

The caller passes:

- `source`: the root-relative source path (for example `docs/payments/SAD.docx`)
- `read_from`: the file to read. That is the normalized markdown (`{run_dir}/sources/<source>.md`) for `.docx` and `.pdf`, or `source` itself for `.md` and `.mdx`
- `taxonomy_dir`: read `quality-attributes.md`, `business-drivers.md`, `nfr-priorities.md`, and `nfr-registry-log.md` (for column definitions) from here
- `output`: where to write the result (`{run_dir}/mined/<source>.md`)

Write only to `output`. Never touch `state.yaml`, `nfr-registry-log.md`, or another file's output.

## Rules

1. **Evidence only.** Record only what the source states. Never add a requirement that the text does not mention. Never "complete" a requirement with a value the source does not give.
2. **Verbatim.** `Verbatim evidence` is the exact sentence (or table row) from `read_from`, copied character for character. Shorten it with `...` only when it is longer than about 300 characters.
3. **Citation.** `Source` points at the line in `read_from` that contains the evidence:
   - `.md` / `.mdx`: `docs/nfr.md:L88`
   - `.docx`: `SAD.docx (SAD.docx.md:L42)`
   - `.pdf`: `notes.pdf p12 (notes.pdf.md:L310)`. The page is the nearest `<!-- page N -->` marker above the line.

   Count lines from 1 in `read_from`. Check each reference before writing it.
4. **One statement, one candidate.** Split a sentence that states two targets. Keep a table row that states one target as one candidate.

## Classify

**NFR Type**

| Type | Use when the statement ... |
| --- | --- |
| `BD` | states what the business gains or loses and by when: money, a date, or market position. Follow the discriminator in `business-drivers.md`: if a CI test could assert it, it is **not** a BD |
| `QAR` | states a quality the system must exhibit and maps to a `quality-attributes.md` row |
| `CSTR` | fixes a design choice: a mandated technology, vendor, regulation, standard, hosting, or process |
| `ASM` | is taken as true without verification (for example "we assume peak load will not exceed ...") |
| `TBD` | is clearly non-functional but fits none of the above, or needs a category that is not in the vocabulary |

**NFR Category.** For `QAR` and `BD`, copy the name **verbatim** from the catalog, for example `Performance & Scalability`, never "Performance". For `CSTR`, `ASM`, and `TBD`, leave it empty unless a catalog name clearly fits.

**Metrics.** Fill in the measurable target the source states (value, unit, and conditions), for example `p95 < 300 ms @ 500 TPS`. Leave it empty when the source gives none. Never estimate one.

**Confidence.** Give one combined score using these anchors:

| Score | Meaning |
| --- | --- |
| 95 | explicit statement, unambiguous category, measurable metric stated |
| 85 | explicit statement, unambiguous category; no metric needed (`CSTR`/`ASM`), or a `BD` with money, date, or market position |
| 70 | category inferred between candidates, or a `QAR` without a metric |
| 50 | vague statement ("fast", "secure"): category guessable, nothing measurable |
| < 40 | functional behaviour, or outside the vocabulary: goes to **Dropped** |

Pick the nearest anchor. Do not interpolate beyond ±5.

**Priority.** Set it only when the source states a business impact that matches a definition in `nfr-priorities.md` (for example "outage stops all card payments" matches **Critical**). Quote that impact in `Interpretation`. Otherwise leave it empty. A missing priority alone is **not** an open question.

**Interpretation.** Write one or two short sentences covering why this type, why this category, why this priority (if one is set), and why this confidence. Example: `QAR: response-time target; Performance & Scalability (latency). Conf 95: explicit, p95 metric stated. No impact stated -> no priority.`

## Status

Set exactly one of these statuses. Never use any other:

- **`Auto`**: confidence ≥ 85 **and** the entry is complete for its type:

  | Type | Complete when it has |
  | --- | --- |
  | all | verbatim evidence, a valid citation, and a vocabulary category (`QAR`/`BD`) |
  | `QAR` | + `Metrics` |
  | `BD` | + money, a date, or a market-position figure |
  | `CSTR` | + what it restricts |
  | `ASM` | + what is assumed, and what breaks if it is false |
  | `TBD` | never `Auto` |

  Priority is **not** required for `Auto`.
- **`TO REVIEW`**: anything else that is non-functional. Each one gets at least one open question naming its gap.
- **`Drop`**: functional behaviour, duplicates within this file, or noise. Write it only to `## Dropped`, never to `## Candidates`.

## Open questions

Write one question per gap, phrased so that a reviewer can answer it in one line, for example "What p95 latency target applies to checkout?".

`Proposed default` may be filled **only** to close a gap in a requirement the source states. For example, the source gives "99.9% availability" but no window, and you propose "monthly". Set `Default by` = `SKILL`. Never propose a requirement the source does not mention. A proposed default never makes an entry `Auto`.

Also raise a question, instead of guessing, when:
- the source contradicts itself within this file
- a candidate maps to no catalog name
- the type is unclear

## Output format

Write `output` exactly in this shape. The main thread parses it. Local IDs are `L-1`, `L-2`, ... for candidates and dropped items (one sequence), and `LQ-1`, `LQ-2`, ... for questions.

```markdown
# Mined: docs/payments/SAD.docx

- source: docs/payments/SAD.docx
- read_from: ai-workflow/nfr-state/<run>/sources/docs/payments/SAD.docx.md

## Candidates

| Local ID | NFR Type | NFR Category | Verbatim evidence | Metrics | Source | Interpretation | Confidence | Priority | Status |
| -------- | -------- | ------------ | ----------------- | ------- | ------ | -------------- | ---------- | -------- | ------ |
| L-1 | QAR | Performance & Scalability | "Checkout must respond within 300 ms at p95." | p95 < 300 ms | SAD.docx (SAD.docx.md:L42) | QAR: latency target; P&S. Conf 95: explicit + metric. No impact -> no priority. | 95 | | Auto |
| L-2 | QAR | Resilience | "The platform must be highly available." | | SAD.docx (SAD.docx.md:L57) | QAR: availability; Resilience. Conf 50: vague, no target. | 50 | | TO REVIEW |

## Open Questions

| # | Question | Local ID | Proposed default | Default by |
| - | -------- | -------- | ---------------- | ---------- |
| LQ-1 | What availability target and measurement window apply to the platform? | L-2 | | |

## Dropped

| Local ID | Text | Source | Why dropped |
| -------- | ---- | ------ | ----------- |
| L-3 | "Users can export invoices to CSV." | SAD.docx (SAD.docx.md:L88) | functional behaviour |

## Summary

candidates: 2 | auto: 1 | to_review: 1 | dropped: 1 | questions: 1
```

- Escape `|` inside cells as `\|`. Keep each row on one line.
- A file with nothing to report still gets all four sections, with empty tables and `candidates: 0`.

## Return

When running as a subagent, return only the `Summary` line and the `output` path. The main thread reads the file itself.
