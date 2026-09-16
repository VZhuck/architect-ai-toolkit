# Mining subagent brief

This is the brief handed to each mining subagent — **one agent per source file, dispatched in parallel**. Source contents stay inside the agent; only candidate rows come back.

Everything the agent needs must be in its prompt. It cannot see the conversation, and **it cannot ask a question** — so it never elicits, never proposes a target the sources do not support, and never decides anything a gate is for.

## Composing the prompt

Send each agent:

1. The **one** source file path it owns.
2. The full text of `templates/business-drivers.md` and `templates/quality-attributes.md` — inline, not as paths. The closed vocabulary must be literally present in the agent's context.
3. The full text of `references/discriminators.md`.
4. The output schema below.
5. The instructions below, verbatim.

Dispatch all agents in a single message so they run concurrently.

## Instructions given to the agent

> Read the source file assigned to you in full. Extract every candidate non-functional requirement signal. Apply the discriminator ladder to each. Return only the table described in the output schema — no preamble, no summary, no commentary, no file contents.
>
> Look for:
>
> - **Quantities attached to behaviour** — "under two seconds", "10k concurrent users", "99.9%", "within one business day", "up to 50 GB".
> - **Modal and comparative language** — "must never", "should always", "as fast as", "at least", "no more than", "even if".
> - **Failure and load talk** — peak periods, seasonal spikes, outages, degraded modes, disaster recovery, backups, retries.
> - **Named non-functional concerns** — security, privacy, audit, compliance (GDPR, HIPAA, PCI, SOC 2), accessibility (WCAG), localization, observability, supportability, portability, interoperability, cost/TCO.
> - **Pain narratives** — "falls over every month-end", "support can't tell what happened". Convert these into requirements and mark the metric `(proposed)`.
> - **Off-hand constraints** — "we're an Azure shop", "the team only knows Java", "it has to ship before the fiscal year ends".
>
> Rules you must follow:
>
> - **The catalogs are closed.** Use attribute names exactly as they appear — same wording, casing, and ampersands. Never invent, split, merge, paraphrase, or re-case a name. If a candidate fits no catalog row, set `kind` to `open-question` and leave `attribute` empty. Do not guess a near-miss.
> - **Quote verbatim.** The `evidence` column carries the source sentence as written, not your paraphrase of it. Trim only surrounding whitespace.
> - **Split compound statements** into separate rows before classifying — but only where each part stands on its own as a requirement, constraint, or driver.
> - **Never emit a fragment as its own row.** A clause that only qualifies another statement — "Under load though.", "It didn't cope.", "That's a hard date." — belongs merged into the row it qualifies, as part of that row's conditions or interpretation. Ask of every row: *could a reviewer act on this alone?* If not, it is not a row. Over-splitting is the most common failure in this step: it inflates the candidate count, fragments one requirement across several rows, and pushes work onto the user at the classification gate.
> - **One row per candidate, even when it touches two attributes.** Where a single statement genuinely supports two different attributes — "falls over every month-end and we manually restart the workers" is both `Resilience` and `Operability` — emit the row once under the attribute it most directly evidences, and name the second attribute in `interpretation`. The caller decides whether to split it.
> - **Never invent a number.** If the source states no target, record what it does say and set `metric` to `(proposed)` with your suggested value, or leave it empty. Never present a value the source does not support as though it were stated.
> - **Do not set priorities.** Priority is decided at a gate you are not part of.
> - **Do not deduplicate across files.** You see one file; the caller merges.
> - **Carry no gossip.** Source material contains names and opinions. Extract the requirement, not who argued for it.
> - If the file contains no non-functional signal at all, return the header row only.

## Output schema

A single markdown table, exactly these columns, in this order:

| evidence | location | kind | attribute | interpretation | metric |
| --- | --- | --- | --- | --- | --- |

| Column | Contents |
| --- | --- |
| `evidence` | the verbatim source sentence |
| `location` | `filename:Lnn`, or `filename:§heading` where lines are not meaningful |
| `kind` | one of `driver`, `qar`, `constraint`, `assumption`, `dropped`, `open-question` |
| `attribute` | the exact catalog name, or empty for `constraint`, `assumption`, `dropped`, `open-question` |
| `interpretation` | one line on what it means as a requirement |
| `metric` | the target if the source states one; `(proposed) <value>` if inferred; empty if neither |

Pipe characters inside a cell are escaped as `\|`.

## What the caller does with the result

The main thread, not the agent:

1. Merges every batch and deduplicates semantically across files — the same requirement stated in two meetings is one row, with both locations recorded.
2. **Validates every `attribute` value against the catalogs and rejects the batch if one is absent.** Re-request that file rather than accepting or silently correcting the name. This is how the closed vocabulary is enforced rather than merely stated.
3. Records genuine conflicts — two sources, different targets — in the trace file's Conflicts table, naming both, choosing neither.
4. Assigns `BD-nn` and `QAR-nn` identifiers.
5. Runs the classification gate with the user.
