# nfr-miner fixture set - expected outcome

Run: `archy-nfr-miner` with `path=test-data/nfr-miner/`.

| Source | Statement | Expected |
| --- | --- | --- |
| payments-nfr.md | Checkout p95 300 ms @ 500 TPS | QAR / Performance & Scalability, Metrics set, Auto |
| payments-nfr.md | Admin console should be fast | QAR, conf <= 70, TO REVIEW + open question |
| payments-nfr.md | Payment API highly available | QAR / Resilience, conf 50, TO REVIEW + open question |
| payments-nfr.md | RTO 1 hour | QAR / Resilience, **conflicts** with payments-sad.docx RTO 4 hours |
| payments-nfr.md | Export invoices to CSV | **Dropped**: functional behaviour |
| payments-nfr.md | Azure in EU regions | CSTR, Auto |
| payments-nfr.md | Peak load <= 2,000 TPS | ASM (Auto only if "what breaks" is derivable, else TO REVIEW) |
| payments-sad.docx | PCI-DSS 4.0 by 30/06/2027, EUR 2m penalty | BD / Risk & Compliance, Auto |
| payments-sad.docx | RTO 4 hours | QAR / Resilience, conflict C1 |
| payments-sad.docx | Availability 99.95% monthly (table) | QAR / Resilience, Auto |
| security-policy.pdf | Encrypt personal data at rest, AES-256 | QAR / Security & Privacy, cited with page (p1) |
| security-policy.pdf | Audit logs retained 7 years | QAR / Auditability & Compliance, p2 |
| security-policy.pdf | Patch critical CVEs within 72 hours (table) | QAR / Security & Privacy, p2 |
| scanned-appendix.pdf | (image only) | file **failed**: no extractable text |
