# Requirements Workshop — Payments Platform Replatform

**Date:** Wednesday, September 2, 2026, 09:00–11:00
**Attendees:** Priya Nair (Enterprise Architect), Tom Alvarez (Product), Rachel Kim (Compliance), Dan Okafor (Platform Engineering)

---

**Tom Alvarez:** Let's start with why we're doing this at all. The board signed off because checkout conversion is bleeding. Cart abandonment is sitting above 12% and finance costed that at roughly £400k a quarter in lost revenue.

**Priya Nair:** Do we know what's driving the abandonment?

**Tom Alvarez:** Mostly speed. The analytics are pretty unambiguous — once checkout goes past about two seconds people start dropping. Marketing wants it well under that on the top journeys.

**Dan Okafor:** Under load though. Month-end is the problem, not a Tuesday afternoon. The current system falls over every month-end and we end up manually restarting the payment workers.

**Priya Nair:** How bad is month-end?

**Dan Okafor:** Last close we peaked around 500 concurrent users and about 1,000 transactions per second. It didn't cope.

**Rachel Kim:** I need to put a marker down on compliance before we go further. ContosoX faces a €2m penalty if we don't achieve PCI-DSS 4.0 certification by 30 June 2027. That's a hard date, it's in the acquirer agreement.

**Priya Nair:** Understood. Is that the only regulatory exposure?

**Rachel Kim:** The other one is data subject rights. The system shall be compliant to GDPR; PII must be removed no later than 30 days after a request is received. We've been failing that manually and it's flagged in the last audit.

**Priya Nair:** Those are different kinds of thing, I'll deal with them separately in the document.

**Dan Okafor:** On the platform side — we're an Azure shop, and legal have said deployment is restricted to EU regions for data residency. That's not negotiable, it came out of the March legal review.

**Priya Nair:** Noted. What about recovery? If a region goes, what's acceptable?

**Dan Okafor:** Honestly nobody's ever written it down. We'd need to agree it.

**Rachel Kim:** Same for how long we retain transaction records — I think it's seven years but I'd want to confirm rather than guess.

**Tom Alvarez:** One more from my side. Support can't tell what happened when a payment fails. Every incident turns into a three-hour archaeology exercise across four log systems.

**Priya Nair:** That's an operability problem, I'll capture it.

**Dan Okafor:** And new engineers take forever to get productive — we lost about three weeks of Anya's time just getting her local environment working.

**Tom Alvarez:** Also, users should be able to save a card for later. That's a hard requirement from product.

**Priya Nair:** That's functional, it goes in the functional spec rather than this one.

**Tom Alvarez:** Fair enough.

**Rachel Kim:** Last thing — accessibility. We're selling into the public sector next year so we need WCAG 2.2 AA across the public journeys.

**Priya Nair:** Good. I'll draft the NFR section and come back with the numbers we still need to agree.
