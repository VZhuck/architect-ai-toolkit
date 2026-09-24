# Business Drivers & Goals

Closed vocabulary for the **Business Drivers & Goals** section of a Non-Functional Requirements document. Attribute names are used verbatim — never shortened, split, merged, paraphrased, or re-cased. This catalog is not extended by tooling; adding a driver is a deliberate human edit to this file.

A business driver states what the business gains or loses, and by when. It carries money, a date, or market position — never a mechanism, threshold, or measurement. Anything a fitness function could assert is a **quality attribute requirement**, not a driver; record it in the Quality Attribute Requirements section and trace it back to the driver it serves.

| Business Driver | Brief Description | Typical Metric / Fitness Function |
| --- | --- | --- |
| **Time to Market** | Speed at which an idea becomes delivered value; the attribute others get traded against under deadline pressure. | Lead time for change; feature cycle time; deployment frequency |
| **Increase Revenue** | Architecture's contribution to top-line growth — new markets, channels, products, and customer outcomes it makes possible. | Revenue per new capability; conversion / retention rate; time-to-first-revenue |
| **Cost Optimization** | Full lifetime economics: build, run, change, retire — including the marginal cost of each future modification. |  TCO over 3–5 years; cost per transaction / per tenant; % capacity on maintenance vs. new work |
| **Risk & Compliance** | Business loss from non-conformance, failure, or breach — fines, licence loss, litigation, market-access restriction. Capture only the high-level business goal and its exposure here; every low-level control detail belongs under Quality Attribute Requirements. |  Open control gaps by severity; potential penalty exposure; certification / audit status |

## Worked examples

| Statement | Verdict | Where it belongs |
| --- | --- | --- |
| "ContosoX incurs a €2m penalty if PCI-DSS 4.0 certification is not achieved by 30/06/2027." | ✓ business driver | Business Drivers & Goals, under **Risk & Compliance** |
| "Cart abandonment above 12% costs approximately £400k per quarter." | ✓ business driver | Business Drivers & Goals, under **Increase Revenue** |
| "System shall be compliant to GDPR; PII removed no later than 30 days after a request is received." | ✗ not a driver | Quality Attribute Requirements, under **Security & Privacy** — a fitness function could assert it |
| "Checkout must complete in under two seconds." | ✗ not a driver | Quality Attribute Requirements, under **Performance & Scalability** |

The discriminator in one line: **if you could write a CI test for it, it is a quality attribute requirement, not a business driver.**
