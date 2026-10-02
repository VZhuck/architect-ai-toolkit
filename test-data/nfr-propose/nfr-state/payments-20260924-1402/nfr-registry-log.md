# NFR Registry Log

## NFR Registry

| NFR ID  | NFR Type | NFR Category | Verbatim evidence | Metrics | Source | Interpretation | Confidence | Priority | Status | Comments |
| ------- | -------- | ------------ | ----------------- | ------- | ------ | -------------- | ---------- | -------- | ------ | -------- |
| NFR-001 | QAR | Performance & Scalability | "Checkout must respond within 300 ms at p95 under 500 TPS." | p95 < 300 ms @ 500 TPS | `test-data/nfr-miner/payments-nfr.md:L5` | QAR: latency target; P&S. Conf 95: explicit + metric. | 95 | High | Confirmed | |
| NFR-002 | QAR | Resilience | "The payment API must be highly available." | 99.9% monthly | `test-data/nfr-miner/payments-nfr.md:L11` + USER | QAR: availability; Resilience. Outage stops all card payments -> Critical. | 85 | Critical | Confirmed | Q1: 99.9% monthly confirmed |
| NFR-003 | QAR | Resilience | "Recovery time objective (RTO) for the payment API is 1 hour." | RTO 1 h | `test-data/nfr-miner/payments-nfr.md:L13` | QAR: recovery target; Resilience. Conf 95. | 95 | | Confirmed | |
| NFR-004 | QAR | Performance & Scalability | "The admin console must load any page within 2 seconds at p95." | p95 < 2 s | `test-data/nfr-miner/payments-nfr.md:L7` | QAR: latency target; P&S. Conf 95. | 95 | | Auto | |
| NFR-006 | QAR | Operability | "The platform should be easy to operate." | | `test-data/nfr-miner/payments-nfr.md:L9` | QAR: operability; vague. Conf 50. | 50 | | TO REVIEW | |

## Open Questions

| # | Question | NFR ID | Proposed default | Default by | Comments | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Q1 | What availability target applies to the payment API? | NFR-002 | 99.9% monthly | SKILL | accepted in review | Closed |
| Q2 | What operability target (e.g. MTTD, manual interventions) applies to the platform? | NFR-006 | | | | TO REVIEW |

## Conflicts

| # | NFR Type | NFR Category | NFR IDs | Value A | Source A | Value B | Source B |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Dropped

| NFR ID | Text | Source | Why dropped | Dropped by |
| ------ | ---- | ------ | ----------- | ---------- |
| NFR-007 | "Users can export invoices to CSV." | `test-data/nfr-miner/payments-nfr.md:L17` | functional behaviour | SKILL |
