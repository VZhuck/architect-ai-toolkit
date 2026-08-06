# Meeting Notes — Landing Zone Networking Design Review

**Date:** Thursday, August 6, 2026, 10:00–10:45 AM
**Location:** Microsoft Teams
**Attendees:**
- Priya Nair — Enterprise Architect
- Marcus Webb — Network Engineering Lead
- Sofia Ramirez — Network Security Engineer
- Dan Okafor — Cloud Platform Engineer (joined late)

---

**Priya Nair:** Thanks for jumping on, I know it's a short one. I wanted to close out the networking section of the SAD before I send it up for sign-off Friday. Marcus, did you and Sofia get a chance to look at the hub-spoke draft I sent Tuesday?

**Marcus Webb:** Yeah, we went through it yesterday. Mostly good. Couple of things we want to flag before it's "final."

**Priya Nair:** Go for it.

**Marcus Webb:** First one — the address space. You had the hub at a /16, 10.10.0.0/16. That's... a lot. We're not going to need 65,000 addresses in the hub for a firewall, a gateway subnet, and Bastion.

**Priya Nair:** I padded it on purpose so we're not boxed in later if we add more shared services. But I hear you — what would you propose instead?

**Marcus Webb:** Honestly a /20 covers everything we've scoped plus room to double it. Sofia, you agree?

**Sofia Ramirez:** Yeah, /20 is plenty for hub. I'd rather we keep the /16 budget for the spokes side since that's where it'll actually get consumed — corp, online, data landing zones are each going to want a decent chunk.

**Priya Nair:** Okay, that's fair, I was thinking about it backwards. So hub at /20, and we carve the /16 across the spokes instead. I'll redo the IPAM table tonight.

**Marcus Webb:** Works for us.

**Priya Nair:** Next thing — DNS. Right now the draft has two custom DNS VMs in the hub, active-passive, forwarding to on-prem for the corp zones. Is that still what we want, or were you looking at something else?

**Sofia Ramirez:** We actually tested the Private DNS Resolver last sprint for the identity migration and it held up fine, including conditional forwarding back to on-prem AD DNS. I'd rather not carry two more VMs we have to patch and monitor forever if the managed service does the job.

**Marcus Webb:** Same. VMs were only ever the fallback because Resolver wasn't GA when we started this. It's GA now, no reason to keep the workaround.

**Priya Nair:** No objection from me, that removes a whole subsystem from the design. I'll swap the DNS VM boxes in the diagram for the Resolver and drop the patching runbook item.

**Marcus Webb:** One more, and this is the one I actually wanted to talk through live rather than over email. The ExpressRoute and VPN gateways — draft has them as active-active for load sharing. We don't think that's necessary and it complicates the routing story with BGP weights we'd have to keep tuning.

**Priya Nair:** What's the alternative — active-passive with VPN as failover only?

**Marcus Webb:** Right. ExpressRoute primary, VPN purely as a cold failover path if the circuit drops. Simpler routes, and honestly our ER circuit SLA is good enough that we're not gaining much from active-active.

**Sofia Ramirez:** Agreed, and it's one less thing for us to explain in the DR runbook.

**Priya Nair:** Okay — ExpressRoute primary, VPN failover-only, no active-active. I'll update the connectivity section.

**Dan Okafor:** Sorry, joining late — did I miss the firewall SKU discussion? I saw a comment thread about that.

**Priya Nair:** Not yet, go ahead, that one's still open.

**Dan Okafor:** So Standard doesn't give us TLS inspection, and Security flagged last month that they want outbound TLS inspection on the online landing zone at minimum, maybe corp too eventually. That pushes us to Premium.

**Sofia Ramirez:** Yeah, that's actually a hard requirement from our side, not a nice-to-have. Standard was fine for the PoC but we can't ship without inspection on anything internet-facing.

**Marcus Webb:** Cost delta's noticeable but it's a platform cost, not per-workload, so I don't think it's a blocker. Priya, is that a budget conversation you need to have separately?

**Priya Nair:** I'll flag it to the sponsor but I don't expect pushback — it's a compliance requirement more than a preference at that point. Let's lock Premium for the hub firewall.

**Marcus Webb:** One last thing, smaller — for spoke-to-spoke traffic, is that going through the firewall or just NSGs plus UDRs?

**Priya Nair:** What's your preference?

**Sofia Ramirez:** Force it through the firewall. We want the east-west traffic logged and inspectable in the same place as north-south, otherwise we've got a blind spot in Sentinel.

**Marcus Webb:** That does mean every spoke needs a UDR pointing default and inter-spoke ranges at the firewall's private IP instead of just relying on VNet peering's default routing. It's not hard, just means we own the route tables centrally rather than leaving it implicit.

**Priya Nair:** That's the right trade-off for visibility. Let's do that — all inter-spoke and outbound traffic routed through the firewall, UDRs managed centrally by your team.

**Marcus Webb:** Understood, we'll own that.

**Priya Nair:** Good, I think that's everything on the technical side. Now the less fun part — timeline. I need to give the steering group a start date for implementation.

**Dan Okafor:** Where are we landing?

**Priya Nair:** Four weeks out. That's not arbitrary — procurement confirmed this morning that stands up the new Azure EA tenant and the initial subscriptions, and realistically that's the critical path, everything else we could start sooner but there's no point spinning up build work against a tenant that doesn't exist yet.

**Marcus Webb:** Four weeks is fine on our end, gives us time to finish the IPAM rework anyway.

**Priya Nair:** Great, I'll put four weeks in the plan and note the tenant procurement as the driving dependency, not our design work.

**Sofia Ramirez:** Sounds good.

**Priya Nair:** Thanks all, I'll circulate the updated diagram and IPAM table by tomorrow and we can do a final five-minute check before it goes to sign-off.

---

*Notes captured by Priya Nair. Action items: update address plan (hub /20, spokes carved from /16), swap DNS VMs for Private DNS Resolver in diagram, update connectivity section to ExpressRoute-primary/VPN-failover, confirm Premium firewall SKU with sponsor, add centrally-managed UDRs for spoke-to-spoke routing, circulate revised diagram and IPAM table before Friday sign-off.*
