---
applyTo: "functional-requirements-raw/**/*.md"
description: "Use when creating or updating markdown files in functional-requirements-raw folder; enforce capability/feature naming and required sections from ADO work items."
---

# Raw Requirements File Rules

Use this instruction only for files under `functional-requirements-raw/`. 

## File Naming Format

Create markdown files using one of these patterns (use kebab-case for names):

|  |- `capability-<capabilityId>.md`   # Capability details (title, description, acceptance criteria)
|  |- `feature-<featureId>.md`   # Work item, which represent latest snapshot of ADO feature
|  |- `req-sync-log.md`   # log of latest sync-req agent run, always created new for each agent run.

## Required File Sections

### Capability and Feature Files
Each capability (`capabilit-<capabilityId>.md` ) & feature (`feature-<featureId>.md`) file must contain the following sections and order:

```markdown
---
id: <ID from ADO>
title: <title from ADO>
---

# Title

## Description
original description taken from ADO in markdown format (no HTML tags, inline styles, etc)

## Acceptance Criteria
original acceptance criteria taken from ADO in markdown format (no HTML tags, inline styles, etc)

```

### `req-sync-log.md` Sync Log File
The file must contain summary of latest sync-req agent run. It should include the following structure:

```markdown
# Capability <capabilityId> - <title>
status: updated/created/unchanged/deleted 

**Summary of Changes**:
highlights changes summary as bullet points. add `**Disagree**` if requirements before and after contradicts each other.

## Feature <featureId> - <title> (for each feature in the sync)

status: updated/created/unchanged/deleted 

**Summary of Changes**:
highlights changes summary as bullet points. add `**Disagree**` if requirements before and after contradicts each other.
```

## File Content Rules
- Use ADO work item content as the source of truth.
- Keep ADO description and acceptance criteria in markdown format
- Strip HTML tags and inline styling if present in the source
- Expect ADO rich text fields to arrive as HTML; convert them into readable markdown headings, bullets, paragraphs, and tables where practical
- Preserve material content even when exact rich-text fidelity is not possible
- Do not add interpretation, summarization, or architecture commentary to raw requirement files

