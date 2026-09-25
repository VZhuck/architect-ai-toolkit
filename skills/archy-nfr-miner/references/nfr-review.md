# NFR Review Loop

A reusable procedure for walking the user through the items of an NFR registry and applying their decisions. Other NFR skills can reuse it by passing a different `scope`.

**Run this in the main conversation only. Never run it in a subagent**, because subagents cannot talk to the user.

## Inputs

| Input | Meaning | archy-nfr-miner passes |
| --- | --- | --- |
| `registry_file` | the `nfr-registry-log.md` to edit | `{run_dir}/nfr-registry-log.md` |
| `state_file` | the `state.yaml` to log to and park in | `{run_dir}/state.yaml` |
| `taxonomy_dir` | for validating categories and priorities | resolved `taxonomy_dir` |
| `scope` | which rows are reviewable | whole registry |
| `allowed_decisions` | the commands that are accepted | all, see [Commands](#commands) |
| `stage_label` | written to `state_log.gate` | `stage-2-review` |

## 1. Present

Show **one overview table** of every entry in `scope`, including `## Dropped` rows. Group the rows in this fixed order and keep `NFR ID` order inside each group:

| # | Group | Rows |
| - | ----- | ---- |
| 1 | Conflicts | entries named in an open `## Conflicts` row |
| 2 | Undecided type | `NFR Type` = `TBD`, status `TO REVIEW` |
| 3 | To review | other `TO REVIEW` entries |
| 4 | Auto | `Auto` entries |
| 5 | Dropped | `## Dropped` rows, as a last chance to push back |

```
Review · 12 entries · 6 open questions · 1 conflict · 8 without priority · 2 dropped

| NFR ID  | Type | Category                  | Statement                          | Status    | Conf | Prio | Open   |
| ------- | ---- | ------------------------- | ---------------------------------- | --------- | ---: | ---- | ------ |
| NFR-004 | QAR  | Resilience                | Monthly availability               | TO REVIEW |  70% | -    | Q2, C1 |
| NFR-010 | TBD  | -                         | "Easy to use"                      | TO REVIEW |  40% | -    | Q5     |
| NFR-002 | BD   | Cost Reduction            | Cut hosting spend 20% by FY27      | TO REVIEW |  70% | -    | Q1     |
| NFR-001 | BD   | Revenue Growth            | EU checkout live by 2027-03-31     | Auto      |  92% | Crit |        |
| NFR-003 | QAR  | Performance & Scalability | p95 checkout < 2 s @ 500 conc.     | Auto      |  90% | -    |        |
| NFR-013 | -    | -                         | "Add PDF invoice export"           | Drop      |    - | -    | functional |

a 3 · a @auto · d 5 <why> · u 13 · p 1,3 High · t 9 <why> · q2=<v> · q2 ok · c1 a|b|both · park
```

- Header line: `entries` counts registry rows in scope only; dropped rows are counted separately (`2 dropped`), never in `entries`.
- `Statement`: the metric if there is one, otherwise the shortest faithful paraphrase of the evidence. Keep it under 40 characters.
- `Open`: the entry's open `Q#` and `C#`. For a dropped row, the `Why dropped` reason in short.
- `Prio`: `Crit`, `High`, `Med`, `Low`, or `-`.

Then ask for the mode (with the ask-question tool if the host has one):
- **guided** - walk the entries that need an answer, one card each (recommended)
- **commands** - answer from the table with [commands](#commands)
- **park** - save and stop; resume later with the same path

## 2. Collect

### Guided mode

**One card per entry** in groups 1-3: a single ask-question call whose tabs are, in this order:

| Tab | Header | Options |
| --- | ------ | ------- |
| each open question | `Q2 <topic>` | the `Proposed default` with its `Default by` (`SKILL`/`USER`); values the sources state; `TBD` |
| each conflict | `C1 Conflict` | `A: <value> (<source>)`; `B: <value> (<source>)`; `Keep both` |
| missing priority | `Priority` | `Critical`, `High`, `Medium`, `Low`, each with its definition from `nfr-priorities.md` in brief |
| decision | `Decision` | `Accept`, `Accept as TBD`, `Drop`, `Skip` |

- An open question that only mirrors a conflict ("C1: which target applies...") gets no tab of its own: the `C#` tab answers it, and resolving the conflict closes it. Likewise `c1 a|b|both` closes it in command mode, and `Open` lists just `C1`.
- The **first tab's question text** carries the entry header: `NFR-004 · QAR · Resilience · conf 70% · TO REVIEW`, the verbatim evidence, and its source citation.
- The host adds a free-text option ("Other") to every tab: treat it as a typed value (`Q2 = "<text>"`, a drop reason, a comment).
- The submit step comes after the last tab. Apply all answers of the card in **one pass**, then echo.
- The tool allows at most 4 tabs. If an entry needs more, ask the first 4 question/conflict tabs, then a follow-up with the rest. `Priority` and `Decision` always go in the last call, and `Decision` is always last.
- `Decision = Accept` while a question tab was answered `TBD` makes the entry `TBD`, not `Confirmed`.
- `Decision = Drop` asks for no extra reason: use the free text if given, otherwise "rejected in review".

After the cards, three **bulk asks**:
1. **Auto** (group 4): one tab, "Accept all <n> Auto entries?" with `Accept all`, `Accept except...` (the user names the IDs in free text), `Walk them as cards`, and `Leave pending`.
2. **Priorities**: entries still without a priority, one tab per entry (up to 4 per call), options `Critical`, `High`, `Medium`, `Low`. The tab's question text quotes the evidence in brief.
3. **Dropped** (group 5): one tab, "Keep these <n> dropped?" with `Keep all dropped`, `Restore some...` (IDs in free text), and `Leave pending`.

If the host has **no ask-question tool**, show the same card as text (header, evidence, one line per tab with its options) and accept the answers as commands.

### Command mode

The user replies from the table with any number of [commands](#commands), one per line or separated by `;`. Items the user does not mention stay pending. `guided` switches to guided mode for what is left.

## Commands

IDs are `NFR-###` for entries, `Q#` for open questions, and `C#` for conflicts. Commands are case-insensitive. **Wherever an entry ID is expected, its number alone works** (`4` = `NFR-004`), and a list may be written `1,3,8` or `NFR-1,3,8`. Every command has a short and a long form; the hint line shows the short ones.

| Short | Long | Effect |
| --- | --- | --- |
| `a 3` | `NFR-003 ok` | entry → `Confirmed` |
| `a @auto [TYPE]` | `auto ok [TYPE]` | confirm all `Auto` entries in scope (optionally one type) |
| `d 5 <reason>` | `NFR-005 drop <reason>` | entry moves to `## Dropped`, `Why dropped` = reason, `Dropped by` = `USER` |
| `u 13` | `NFR-013 restore` | move a dropped entry back to the registry as `TO REVIEW` |
| `p 7 High`, `p 1,3,8 High` | `NFR-007 prio High`, `prio NFR-1,3,8 High` | set the priority (`Critical`, `High`, `Medium`, `Low`) |
| `t 9 <why>` | `NFR-009 tbd "<why>"` | accepted gap: status `TBD`, reason recorded in `Comments` |
| `n 11 <text>` | `NFR-011 note "<text>"` | append to `Comments`; status unchanged, the item stays pending |
| `q4=<value>` | `Q4 = "<value>"` | answer: apply the value to the linked entry (metric, category, and so on), close the question |
| `q4 ok` | `Q4 ok` | accept the `Proposed default`: apply it, close the question; the entry's `Source` gains `+ USER` |
| `q4 no` | `Q4 no` | reject the proposed default; the question stays open |
| `c1 a`, `c1 b` | `C1 pick A`, `C1 pick B` | the winning entry keeps its value and records "superseded: <value> (<source>)" in `Comments`; the losing entry moves to `## Dropped` (`USER: superseded by NFR-### (C1)`); remove the conflict row |
| `c1 both` | `C1 both` | keep both entries (a free-text answer may re-read one, for example "4 h is the RPO"); record the resolution in `Comments` of both; remove the conflict row |

Resolving a conflict also closes its mirrored open question, with the resolution in its `Comments`. The question and `state_log` are the trace once the conflict row is gone.
| - | `NFR-007 cat <name>` | set the category; the name must exist verbatim in the catalog for the entry's type |
| - | `NFR-007 type <QAR\|BD\|CSTR\|ASM>` | set the type; if the category no longer fits, ask for one. The ID does not change |
| - | `NFR-007 metric "<value>"` | set `Metrics` |
| `skip`, `guided`, `park`, `done` | | flow control |

Reject a command outside `allowed_decisions`, or one with an unknown ID, and say why. Reject a category that is not in the catalog, and list the valid names for that type.

## 3. Apply

Apply all collected decisions to `registry_file` in one edit pass:

- An entry closes (`Confirmed`) only when nothing is still open for it. If `NFR-007 ok` arrives while `Q5` about `NFR-007` is still open, confirm the entry but tell the user that Q5 remains.
- A closed question gets status `Closed`, and its `Comments` records the answer.
- A dropped entry is removed from `## NFR Registry` and added to `## Dropped`. Its open questions close as "entry dropped".
- A restored entry is removed from `## Dropped` and re-added to the registry as `TO REVIEW`.
- Never renumber IDs. Never delete a row outright: anything that leaves the registry goes to `## Dropped`.

Then echo a diff: one line per change.

```
NFR-003: TO REVIEW -> Confirmed
NFR-005: moved to Dropped (USER: duplicate of NFR-003)
NFR-007: prio - -> High
Q4: closed, NFR-011 Metrics = "99.9% monthly"
C1: resolved, NFR-020 keeps "RTO 1 h" (SAD.docx L42); "RTO 4 h" superseded
```

Append one `state_log` entry per apply pass to `state_file`: `gate` = `stage_label`, `change` = a short summary ("7 decisions: 3 confirmed, 1 dropped, 2 prio, 1 question"), and `status` = `finished`. Update `update_on`.

## 4. Repeat

Rebuild the queue with only what is **still pending** or **was revised** by the last pass (for example, a retyped entry that now needs a category), and show the overview table again without asking for the mode. Keep the current mode: in guided mode, continue with the next card.

The loop ends when:
- **the queue is empty**: tell the caller the review is complete
- **`done`**: the remaining items stay pending; tell the caller the review is complete with N items still open
- **`park`**: set `active_step` = `review-parked` in `state_file`, log it, and stop. Stage 0 offers to resume with only the undecided items

## Worked example: guided

```
you> (overview table, as in Present)
     How do you want to review?   [guided]  [commands]  [park]
user> guided

you> ask-question, 4 tabs:
     ┌ Q2 Target ┬ C1 Conflict ┬ Priority ┬ Decision ┬ Submit ┐
     NFR-004 · QAR · Resilience · conf 70% · TO REVIEW
     "The platform shall be highly available on a monthly basis." (RFP.pdf p4 (RFP.pdf.md:L118))
     Q2 What availability figure is committed?
        ○ 99.9% monthly (SKILL)  ○ 99.95% monthly (RFP §4.1)  ○ TBD  ○ Other
     C1 Which source wins?
        ○ A: 99.95% (RFP.pdf p4)  ○ B: 99.9% (meeting-notes.md:L42)  ○ Keep both
     Priority  ○ Critical  ○ High  ○ Medium  ○ Low
     Decision  ○ Accept  ○ Accept as TBD  ○ Drop  ○ Skip

user> Q2: 99.95% monthly (RFP §4.1) · C1: A · Priority: Critical · Decision: Accept

you> Q2: closed, NFR-004 Metrics = "99.95% monthly"
     C1: resolved, NFR-004 keeps "99.95%" (RFP.pdf p4); "99.9%" (meeting-notes.md:L42) superseded
     NFR-004: prio - -> Critical
     NFR-004: TO REVIEW -> Confirmed
     next card: NFR-010 (1/5 left in "Undecided type")
```

## Worked example: commands

```
you> (overview table)
user> commands

user> c1 a; q1 ok; q3=RTO 15 min / RPO 5 min; d 10 too vague; p 1,3 Critical; a @auto

you> C1: resolved, NFR-004 keeps "99.95%"; "99.9%" superseded
     Q1: closed, NFR-002 baseline = "FY26 average" (Source + USER)
     Q3: closed, NFR-005 Metrics = "RTO 15 min / RPO 5 min"
     NFR-010: moved to Dropped (USER: too vague)
     NFR-001, NFR-003: prio - -> Critical
     4 Auto -> Confirmed
     Still pending: NFR-002 (now complete -> a 2?), NFR-004 (Q2 open), NFR-005 (a 5?), 4 without priority, 2 dropped
     (overview table with only those rows)
```
