# Non-Functional Requirements

Non-functional requirements collectively cover the business drivers and goals the solution serves, the quality attribute requirements it is accountable for, the constraints it is built within, and the assumptions it proceeds on.

## Business Drivers & Goals

High-level business outcomes this solution serves. One row per driver from the closed catalog, at most one row per catalog driver. Each states a business consequence with money or a date — never a mechanism, threshold, or measurement.

| ID | Business Driver | Goal / Business Impact | Priority |
| --- | --- | --- | :-: |
| BD-01 |  |  |  |

## Quality Attribute Requirements

Key quality criteria for the solution, identified by the architect and prioritized by stakeholders. Prioritization is the critical step: it identifies the 5–7 most important attributes the solution is optimized for, and tells architects what to trade away. One row per requirement, each stating what is measured, the threshold with its unit, and the conditions.

| ID | Quality Attribute | Requirement | Priority | Driver |
| --- | --- | --- | :-: | --- |
| QAR-01 |  |  |  |  |

## Constraints

Non-negotiable givens that remove design options and cannot be traded off. State the constraint and, in brackets, where it comes from. Measurable "shall" statements are not constraints — they are quality attribute requirements.

- Constraint statement (source, date)

## Assumptions

Design-time beliefs the team is proceeding on, each with its impact if it turns out false. Open questions and unresolved targets do not belong here.

- Assumption (Impact) </br>
assumption details & explanation

<!--
Conventions used in the tables above:

  P0 🔒        priority confirmed by the user and locked; never changed automatically
  P1           priority proposed or inherited, not yet locked
  (proposed)   target value proposed by the tool, awaiting stakeholder confirmation
  TBD          target value still unknown and explicitly deferred
  *new*        row added in the most recent run, not yet reviewed
  —            no business driver traces to this requirement (baseline hygiene)

At most 7 rows across the document may carry P0.
Attribute names come verbatim from templates/business-drivers.md and
templates/quality-attributes.md. Both catalogs are closed vocabularies.
-->
