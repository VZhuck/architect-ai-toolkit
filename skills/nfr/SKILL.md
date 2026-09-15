---
name: nfr-analysis
description: Create and maintain a project's Non-Functional Requirements document from requirements, meeting notes, RFPs, or transcripts, classified against the business/technical quality-attribute catalogs. Use whenever the user mentions NFRs, quality attributes, QAs, "-ilities", SLAs/SLOs, performance or availability targets, architecture constraints, or asks to review notes for quality criteria — including refreshing or reprioritizing an existing NFR document.
arguments-hint:
- path - Directory or exact file to analyze — usually requirements or meeting notes; Fall back - Ask the user. Never guess. |
- nfrPath - Target Non-Functional Requirements document to create or maintain; Use env variable NFR_PATH, or ask user if not set.
---

# NFR Analysis

Turn raw prose (requirements, meeting notes, transcripts, tickets) into a structured, measurable, prioritized Non-Functional Requirements document, classified against the organization's quality-attribute catalogs. The skill is intended for both **initial creation** and **ongoing maintenance** of the same NFR document across many iterations.

## Before Doing Anything
1. resolve `skillTmplDir` directory co-located with this `SKILL.md` file (e.g. `<skill-directory>/templates/`)
1. Load catalog of business quality attributes at `<skillTmplDir>/business-qas.md`
2. Load catalog of technical quality attributes at `<skillTmplDir>/technical-qas.md`
3. Load the priority scale at `<skillTmplDir>/qa-priorities.md`
4. **Hard stop if any of the three catalog files is missing or unreadable.** Do not fall back to ISO 25010, generic "-ilities", or vocabulary mined from the sources. Report which file is missing and ask the user where to find it. The catalogs are the closed vocabulary for this document; without them, this skill cannot run.
5. If `path` is a directory, recurse and collect text-bearing files (`.md`, `.txt`, `.docx`, `.pdf`, `.adoc`, `.csv`). Skip binaries, images, lock files, and `node_modules`-style noise. If the directory holds more than ~30 candidate files, list what you found and ask which subset matters rather than burning context on everything.
6. State the resolved paths (sources, catalog folder `<skillTmplDir>`, target NFR document) in one line before proceeding, so the user can correct you cheaply.

## Workflow

The workflow has two shapes:

- **First run** — no NFR document exists yet. The flow is gated: mine → sort → elicit missing numbers → classify → set metrics → prioritize → **user confirmation** → write. Do not write the target file before the classification, metric, and priority gates have been confirmed in the current conversation.
- **Maintenance run** — an NFR document already exists. Run all steps, but respect locked content (see step 6 and step 8) and merge in place rather than overwriting.

**The target NFR file is written exactly once per run, and only after step 6 is confirmed.** Producing a draft document "for review" before the gates are answered is a violation of this skill.

### 1. Load the catalogs first

Read the quality-attribute catalogs **before** reading the sources. Knowing the organization's vocabulary up front changes what you notice in the prose — you'll spot a throwaway line about "customers abandon the cart if it's slow" as an instance of a catalog attribute rather than background chatter.

Load these three files from the resolved `skillTmplDir` directory (all must be read; do not skip):

- `<skillTmplDir>/business-qas.md` — business-level quality attributes and their business metrics. Drives the **Business Quality Attributes** table.
- `<skillTmplDir>/technical-qas.md` — architect-facing technical quality attributes with baseline priorities and typical fitness functions. Drives the **Quality Attributes** table.
- `<skillTmplDir>/qa-priorities.md` — the priority scale (`P0` / `P1` / `P2` / `P3`) and its meaning. Use this scale unless the existing NFR document already uses a different one — then match the existing document.

Extract from the catalogs: attribute names, definitions, baseline priorities, and canonical metrics. Reuse the catalog's exact names and casing in your output. Divergent naming is the main reason these documents stop being comparable across projects.

### 2. Mine the sources for NFR signals

Read every selected source and pull out candidate statements. NFRs are rarely labelled; they hide in ordinary sentences. Look for:

- **Quantities attached to behaviour** — "under two seconds", "10k concurrent users", "99.9%", "within one business day", "up to 50 GB".
- **Modal and comparative language** — "must never", "should always", "as fast as", "at least", "no more than", "even if".
- **Failure and load talk** — peak periods, seasonal spikes, outages, degraded modes, disaster recovery, backups, retries.
- **Named non-functional concerns** — security, privacy, audit, compliance (GDPR, HIPAA, PCI, SOC 2), accessibility (WCAG), localization, observability, supportability, portability, interoperability, cost/TCO.
- **Pain narratives** — "the current system falls over every month-end", "support can't tell what happened". These imply targets that nobody stated; convert them into requirements and mark the metric as proposed.
- **Off-hand constraints** — "we're an Azure shop", "the team only knows Java", "it has to ship before the fiscal year ends".

For each candidate, record: the verbatim source sentence, the file and location, and your interpretation. Traceability matters more than volume — a reviewer must be able to check your reading against the original.

### 3. Sort candidates into requirement / constraint / assumption

This separation is where most NFR documents go wrong, so be deliberate:

- **Quality attribute requirement** — a measurable property of the solution the team is accountable for achieving. "Checkout completes in under 2s at p95." Almost anything phrased with "shall", "must", or a target value is a requirement, even when the source is an enterprise policy.
- **Constraint** — a non-negotiable given that removes design options and is not something you can "achieve more of". Technology mandates ("must use Pearson enterprise IDAM"), platform/region lock-in, budget ceilings, fixed deadlines, legal jurisdiction, existing systems that must be integrated, team skills, out-of-scope decisions.
- **Assumption** — a design-time belief the team is proceeding on, with a stated impact if it turns out false. Assumptions are not a place to park open questions or missing numbers — those belong in the elicitation gate below.

**Two tests to resolve the requirement-vs-constraint confusion:**

1. *Tradability test.* If a stakeholder could imagine trading it off against another quality attribute ("we'll accept slightly less of X to get more of Y"), it is a **requirement**. If it cannot be traded because it is imposed from outside the team, it is a **constraint**.
2. *Design-option test.* A constraint eliminates options ("only EU Azure regions", "only Java"). A requirement sets a target the team designs toward ("encrypted in transit", "p95 < 2s", "authN/authZ on every hop").

A policy statement like "Pearson enterprise security guidelines shall apply" is a **constraint** only in the sense that the standard itself is externally imposed. The concrete measurable clauses inside that policy (encryption, least privilege, audit logging, etc.) are **requirements** and belong in the Quality Attributes table, not in Constrains.

Drop anything that is actually functional behaviour, and mention what you dropped so the user can push back.

> **Human-in-the-loop gate — hard STOP.** Steps 3.5, 4, 5, and 6 each end with a stop point. At each stop point: present the proposal, list the questions, and **wait for the user's answer in the current conversation before continuing**. Do not write the target file, do not proceed to the next step, and do not paper over missing answers by adding them as "assumptions" or "TBD" rows. Batch questions per step — don't drip-feed. If the user is unavailable, stop and report; do not guess forward.

### 3.5. Elicit missing numbers *(human-in-the-loop)*

Before classifying, scan the candidate list for quality attributes whose target is unstated in the sources — typically availability, RTO/RPO, latency (p50/p95/p99), concurrency and peak load, retention periods, cost caps, and dependency SLAs. These are the numbers the document exists to record; inventing them defeats its purpose.

**Stop and ask the user:**

- One consolidated question block listing each missing number, the attribute it belongs to, and (where useful) a defensible starting value the user can accept, adjust, or reject.
- Any conflicting numbers found across sources — name both, don't pick a winner.
- Any target the sources explicitly mark `TBD` or defer to a named stakeholder.

Wait for the user's answer. Do not move to classification with unanswered numbers, and do not carry them into the final document as `Assumptions` — assumptions are for design-time beliefs, not for deferred elicitation.

### 4. Classify against the catalog *(human-in-the-loop)*

Map every requirement to exactly one **primary** business quality attribute from `business-qas.md`; note a secondary only when the requirement genuinely serves two. Then map the same requirement to the appropriate technical attribute(s) from `technical-qas.md`.

**Catalog fidelity is non-negotiable.**

- Use attribute names **exactly** as they appear in the catalog files (same wording, same casing, same ampersands). Do not shorten, split, merge, or paraphrase them (e.g. do not turn `Security & Privacy` into `Security`, `Identity and Authorization`, or `Privacy and Data Minimization` — those are metrics of the catalog attribute, not new attributes).
- The Business Quality Attributes table draws only from `business-qas.md`. If the catalog has N business attributes, the Business Quality Attributes table has at most N rows.
- The Quality Attributes table draws only from `technical-qas.md`. Same rule.
- Business Quality Attributes describe **business outcomes** — money, time, market position, regulatory exposure. Technical topics (Security, Reliability, Performance, Observability, etc.) never appear in the Business Quality Attributes table; they map underneath through the Quality Attributes table. If you find yourself putting "Security" or "Availability" as a business QA, stop and re-map it under `Risk & Compliance` or the appropriate business catalog row instead.
- When a requirement fits no catalog row, do not invent one. Add it to an "Unmapped candidates" list and propose either the closest catalog attribute or a new catalog entry for the user to approve. A silently mis-filed or invented row is worse than an open question.

**Before continuing to step 5, present to the user:**

- The mapping table (requirement → primary business QA → technical QA), using catalog names verbatim.
- Unmapped candidates with your proposed resolution.
- Any classification you are less than confident about, flagged explicitly.

Wait for the user to confirm, correct, or extend the mapping. **Do not write the target file yet. Do not proceed until they answer.**

### 5. Make every metric measurable *(human-in-the-loop)*

A quality attribute without a metric is a slogan. Rewrite each one so it states **what is measured, the threshold, and the conditions**.

**Example 1:**
Source: "The system should be fast."
Metric: `p95 page load < 2s for the top 10 journeys at 500 concurrent users`

**Example 2:**
Source: "We can't afford another outage like last December."
Metric: `99.95% monthly availability; RTO ≤ 15 min, RPO ≤ 5 min` *(proposed — confirm with business)*

**Example 3:**
Source: "New devs take forever to get productive."
Metric: `New engineer ships a production change within 5 working days; local environment bootstrap < 30 min`

Where the source gives no number, propose a defensible one and mark it `(proposed)` or `TBD — needs stakeholder confirmation`. Proposing a testable starting point is more useful than leaving a blank, as long as the provenance is honest. Prefer scenario form (stimulus → environment → response → measure) when a bare number would be ambiguous.

**Before continuing to step 6, present to the user:**

- Every metric marked `(proposed)` or `TBD`, grouped so they can be reviewed in one pass.
- Any metric where source evidence conflicts (two meetings quoting different SLAs) — name both, don't pick a winner.
- Metrics inherited from an existing NFR document that this batch of sources contradicts.

Wait for stakeholder confirmation on proposed values before treating them as agreed. **Do not write the target file yet.** A `(proposed)` metric may enter the final document only after the user has seen it at this gate and chosen to accept, adjust, or leave it pending.

### 6. Prioritize *(human-in-the-loop; priorities lock once confirmed)*

Priority is the step that gives the document its value: it tells architects what to trade away. Use the scale from `<skillTmplDir>/qa-priorities.md` (`P0` / `P1` / `P2` / `P3`) unless the existing NFR document already uses a different one — then match the existing document.

Start from the baseline priorities in `<skillTmplDir>/technical-qas.md`, then adjust up or down using evidence from the sources (a stakeholder banging the table about latency is evidence; silence is not).

Constrain yourself: **only 5–7 attributes across the whole solution may be `P0`.** If more than seven qualify, force the ranking by asking which the business would sacrifice first, or present the tie-break to the user rather than quietly inflating the list.

**Before writing the document, present to the user:**

- Proposed priority for every attribute, with a one-line reason (evidence from source, or "catalog default").
- The 5–7 chosen `P0` attributes, called out explicitly.
- Any priority that differs from the catalog baseline or from a previously locked value in the existing NFR document.

Wait for the user to confirm.

#### Priority lock rule *(applies from the second run onward)*

Once the user has confirmed priorities and they are written to the NFR document, they are **locked**. Mark each confirmed priority in the document with a `🔒` marker in the priority cell (e.g. `P0 🔒`).

On subsequent maintenance runs:

- **Never** change a locked priority automatically, even if new sources appear to justify it.
- If new evidence suggests a locked priority is wrong, **report the mismatch** in the summary: name the attribute, its locked value, the proposed value, and the source quote/date that triggered the flag. Do not modify the cell.
- Only unlock and rewrite a priority when the user explicitly says so in the current conversation. Record that unlock decision in the summary.
- New attributes added in this run are **not** locked until the user confirms their priority.

### 7. Write or update the document

This step is used for **both** creating a new NFR document and maintaining an existing one. The template below is the shape a fresh document takes; on a maintenance run, the same template is what you merge into. Do not regenerate the file from scratch when it already exists — see step 8.

Use this exact template. Keep the headings as written so existing tooling and reviewers find what they expect.

```markdown
# Non-Functional Requirements (NFR)

## Business Quality Attribures
| Business Quality Attribute| Metric| Priority |
|------|------------|:---:|
|      |            |     |

## Quality Attributes
Summarize key quality criteria for the solution, identified by architect and prioritized by stakeholders. Note, that priority is critical step as it helps to identify key 5-7 the most important quality attributes being prioritized by target solution.

| Quality Attribute | Metric| Priority |
|------|------------|:---:|
|      |            |     |

## Constrains
- <list of constrains goes here>

## Assumptions
- Assumption (Impact) </br>
assumption details & explanation
```

Fill it as follows:

- **Business Quality Attribures** — one row per catalog attribute from `business-qas.md` that this solution actually touches, named **exactly** as in the catalog. The metric column carries a **business** measure (revenue, cost, time-to-market, regulatory exposure, market access) — never a technical measure such as latency, uptime, or MTTR. If the metric you have is technical, it belongs in the Quality Attributes table instead. Priority reflects the stakeholder view of business importance.
- **Quality Attributes** — the solution-level, architect-facing attributes from `technical-qas.md`, each traceable to a business QA above and named **exactly** as in the catalog. This is where technical metrics live. Keep the explanatory paragraph.
- **Constrains** — one bullet per constraint that survives the tradability and design-option tests in step 3. State the constraint and, in brackets, where it comes from. `- Deployment restricted to EU Azure regions (data residency, legal review 2026-03-11)`. Do not put measurable "shall" statements here — those are requirements and belong in the Quality Attributes table.
- **Assumptions** — design-time beliefs the team is proceeding on, with impact if wrong. Follow the template's two-line shape exactly: `- Assumption (Impact)`, then the explanation on the next line. **Open questions, unresolved TBDs, and elicitation follow-ups do not belong here.** If a number is still unknown at write time, either it was accepted at the step 3.5 gate (with a defensible proposed value now in the metric cell) or the write has been deferred until the user answers.

**Priority cell conventions** (apply on both create and update):

- Confirmed priorities carry a `🔒` marker (e.g. `P0 🔒`). This is the lock signal for future runs.
- Priorities proposed in this run but not yet confirmed carry `(proposed)`.
- New rows added in this run carry a trailing `*new*` until the user drops it.

Keep rows terse enough to scan. Long rationale belongs beneath the table or in the source-mapping appendix, not inside a cell.

### 8. Update rather than overwrite

When the document already exists, treat it as authoritative and merge:

- Match existing rows by attribute name and **update in place** — never reorder or re-word rows you aren't changing.
- **Locked priorities (`🔒`) are immutable** in this run. Do not modify them; report mismatches per step 6.
- Preserve human edits, comments, and any extra sections the document has grown. If a stakeholder priority contradicts your reading of the sources, keep theirs and raise the conflict in your reply.
- Metrics may be tightened or clarified in place; if the change is material (threshold moves, conditions differ), leave the previous value in a trailing comment on the row or list it in the summary.
- Add new rows for genuinely new findings; mark them with a trailing `*new*` so a reviewer can find them.
- Never delete a requirement because this batch of notes didn't mention it. Absence of evidence isn't retraction. If something now looks obsolete, propose removal in your reply instead.
- If the existing document uses different heading spellings than the template, keep the existing ones.

### 9. Report back

After writing the file, give the user a short summary covering:

- Paths used (sources, catalog folder, NFR document) and how many sources were read.
- Count of requirements added / updated / unchanged.
- The 5–7 `P0` attributes and the reasoning in one line each.
- **Locked-priority mismatches** — for each locked priority the new evidence contradicts: attribute name, locked value, evidence-suggested value, source quote/date. State clearly that no change was made.
- Unmapped candidates needing a catalog decision.
- Metrics marked proposed or TBD that need stakeholder confirmation.
- Conflicts between sources (two meetings quoting different SLAs) — name both and don't pick a winner silently.

Keep it scannable. The document is the deliverable; the summary just tells the user where to look.

## Judgement calls

- **Sparse sources.** If the material yields almost nothing, say so rather than padding the tables with generic ISO 25010 attributes. Offer to run a short elicitation instead — a handful of targeted questions usually beats guesswork.
- **Contradictions.** Later meeting notes usually supersede earlier ones, but not always; check dates, and when in doubt surface both.
- **Ambitious targets.** "Five nines" alongside a shoestring budget is a real finding. Record the requirement and note the tension in the constraints or your summary — don't quietly soften it.
- **Confidentiality.** Meeting notes contain names and opinions. Carry the requirement into the document, not the gossip.
