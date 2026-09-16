# The discriminator ladder

Every candidate statement is tested in this order. **First match wins.** The order is the point: most misfiled requirements come from applying the right rules in the wrong sequence.

```
 candidate statement
   │
   ├─ 1. Behaviour the system performs?          ──yes──▶ FUNCTIONAL → drop, log why
   │       "user can reset their password"
   │
   ├─ 2. Could a fitness function assert it?     ──yes──▶ QUALITY ATTRIBUTE REQUIREMENT
   │       p95 < 2s · RPO ≤ 5min · WCAG 2.2 AA           → exactly one catalog attribute
   │       "PII purged ≤ 30d of verified request"
   │
   ├─ 3. Removes design options, untradeable?    ──yes──▶ CONSTRAINT
   │       EU regions only · must use enterprise IDAM
   │
   ├─ 4. A belief being proceeded on, with a
   │     stated impact if wrong?                 ──yes──▶ ASSUMPTION
   │
   ├─ 5. Money / time-to-market / market access /
   │     penalty exposure, with a date?          ──yes──▶ BUSINESS DRIVER & GOAL
   │       "€2m penalty if not certified by 30/06/2027"
   │
   └─ 6. none of the above                       ────────▶ OPEN QUESTION
                                                            (trace file only)
```

## Why step 2 comes before step 5

This is the single most important thing on this page.

A compliance statement usually contains both a business consequence *and* a mechanism. Test the mechanism first, or the whole statement lands in the business table and the measurable part is lost.

> "System shall be compliant to GDPR; PII removed no later than 30 days after a request is received."

Step 2 catches it: a fitness function can assert "PII removed ≤ 30 days". It is a **quality attribute requirement** under `Security & Privacy`. It never reaches step 5.

> "CompanyX will face a penalty fee if ComplianceX is not completed by 30/06/2027."

Step 2 does not catch it — there is nothing to assert, no threshold, no mechanism. It falls through to step 5 and is a **business driver** under `Risk & Compliance`.

**The compressed rule: if you could write a CI test for it, it is a quality attribute requirement, not a business driver.**

## Requirement vs. constraint

Two tests, both must agree:

1. **Tradability.** Could a stakeholder imagine trading it against another attribute — "we'll accept slightly less X for more Y"? Then it is a **requirement**. If it cannot be traded because it is imposed from outside the team, it is a **constraint**.
2. **Design options.** A constraint *eliminates* options ("only EU Azure regions", "only Java"). A requirement sets a target the team designs *toward* ("encrypted in transit", "p95 < 2s").

An enterprise policy is a constraint only as to the *standard itself* being externally imposed. The concrete measurable clauses inside it — encryption, least privilege, audit logging — are **requirements**.

## Splitting a compound statement

Source sentences frequently carry more than one candidate. Split them before running the ladder, and run it on each part.

> "We're an Azure shop, so it has to run in EU regions, and checkout can't take more than two seconds or customers abandon — that's costing us about £400k a quarter."

| Part | Ladder step | Outcome |
| --- | --- | --- |
| "run in EU regions" | 3 | Constraint |
| "checkout can't take more than two seconds" | 2 | `QAR` under `Performance & Scalability` |
| "costing us about £400k a quarter" | 5 | `BD` under `Increase Revenue` |

The requirement then traces to the driver, which is exactly the linkage the `Driver` column records.

## Business drivers must stay lean

A driver answers: **what does the business gain or lose, and by when?** At most one row per catalog driver.

| Statement | Verdict |
| --- | --- |
| "ContosoX incurs a €2m penalty if PCI-DSS 4.0 certification is not achieved by 30/06/2027." | ✓ driver — money and a date, no mechanism |
| "Cart abandonment above 12% costs ~£400k per quarter." | ✓ driver — money |
| "Must reach the German market before the FY27 close." | ✓ driver — market access and a date |
| "System shall be GDPR compliant; PII deleted within 30 days." | ✗ requirement — step 2 catches it |
| "99.95% monthly availability." | ✗ requirement — step 2 catches it |

Naming a regulation does not make a statement technical. "PCI-DSS 4.0 certification by 30/06/2027" is a driver; "TLS 1.3 on every hop" is a requirement.

## Pain narratives

Complaints imply targets nobody stated. Convert them, and mark the metric `(proposed)` so the provenance stays honest.

| Source | Becomes |
| --- | --- |
| "The current system falls over every month-end." | `Resilience` — availability and peak-load targets `(proposed)` |
| "Support can't tell what happened." | `Operability` — MTTD and diagnosability targets `(proposed)` |
| "New devs take forever to get productive." | `Maintainability` — onboarding-to-first-change target `(proposed)` |

## What to record for every candidate

Traceability matters more than volume. A reviewer must be able to check the reading against the original.

- the verbatim source sentence
- the file and location
- the interpretation
- the ladder step that classified it
