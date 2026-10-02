# NFR Registry Log

## NFR Registry

| NFR ID  | NFR Type | NFR Category | Verbatim evidence | Metrics | Source | Interpretation | Confidence | Priority | Status | Comments |
| ------- | -------- | ------------ | ----------------- | ------- | ------ | -------------- | ---------- | -------- | ------ | -------- |
| NFR-001 | CSTR | | "Payment processing must comply with PCI-DSS 4.0." | | security-policy.pdf p1 (security-policy.pdf.md:L4) | CSTR: mandated standard. Conf 85. | 85 | High | Confirmed | |
| NFR-002 | QAR | Performance & Scalability | "Admin console pages must load in under 2 s (p95)." | p95 < 2 s | security-policy.pdf p2 (security-policy.pdf.md:L20) | QAR: latency target; P&S. Conf 95. | 95 | | Auto | |
| NFR-003 | QAR | Security & Privacy | "Cardholder data must be encrypted at rest using AES-128." | AES-128 | security-policy.pdf p1 (security-policy.pdf.md:L8) | QAR: encryption at rest; S&P. Conf 95. | 95 | Critical | Confirmed | |
| NFR-004 | QAR | Resilience | "The payment API must recover within 4 hours (RTO)." | RTO 4 h | security-policy.pdf p3 (security-policy.pdf.md:L31) | QAR: recovery target; Resilience. Conf 95. | 95 | | Confirmed | |

## Open Questions

| # | Question | NFR ID | Proposed default | Default by | Comments | Status |
| --- | --- | --- | --- | --- | --- | --- |

## Conflicts

| # | NFR Type | NFR Category | NFR IDs | Value A | Source A | Value B | Source B |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Dropped

| NFR ID | Text | Source | Why dropped | Dropped by |
| ------ | ---- | ------ | ----------- | ---------- |
