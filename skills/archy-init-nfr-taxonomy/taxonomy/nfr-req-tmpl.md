# Non-Functional Requirements

## Business Drivers & Goals

Business drivers and goals are the foundational external forces, internal needs, and strategic objectives that dictate how an organization's structure, processes, and technology must evolve. This section defines the key business drivers and their business-level goals.

| ID | Business Driver | Business Goal | Metric / Criteria | Priority |
| --- | --- | --- | --- | --- |
| BD-001 | Time to Market | Launch EU checkout before the 2027 holiday season to capture seasonal demand. | EU checkout live by 2027-03-31 | Critical |

## Quality Attributes

Architecture quality attributes are the non-functional requirements that define how well a system performs its functions, rather than what functions it performs.

| ID | Quality Attribute | Requirement | Metric / Criteria | Priority |
| --- | --- | --- | --- | --- |
| QAR-001 | Performance & Scalability | Checkout API response time under peak load | p95 < 500 ms @ 500 TPS | High |

## Assumptions

Assumptions are unverified conditions or educated guesses taken as temporary truths to keep a plan moving forward, but they carry risk and must be actively validated over time.

| ID | Assumption | Risk | Impact |
| --- | --- | --- | --- |
| ASM-001 | The solution is hosted on AWS. | The deployment view and technology stack could need to be redesigned if a different platform is chosen (assumed, not yet verified with stakeholders). | High |

## Constraints

Constraints are fixed, non-negotiable boundaries or hard limits (such as a legal regulation or a fixed budget) that must be woven directly into the design.

| ID | Constraint | Impact |
| --- | --- | --- |
| CSTR-001 | AWS cloud-native approach (a non-negotiable constraint from the client). | High |
