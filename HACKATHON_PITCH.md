# NALAM AI — 3-Minute Hackathon Pitch Script

**Speaker Time:** Exactly 3 Minutes (approx. 400–450 words)  
**Presenter Tone:** Empathetic, confident, technologically rigorous  
**Visual Cue:** Have the Web UI on screen (`http://localhost:5173`) with the CLI IVR Simulator open side-by-side.

---

### [0:00 – 0:40] The Problem: The Wasted Journey

*"Judges, imagine you are a daily-wage laborer in a rural village. Your child has a burning fever.*

*You take the day off work—losing a day's food wages. You pay for a crowded bus to the Primary Health Centre 25 kilometers away.*

*You get there, only to discover the doctor was called away on an emergency, and the pharmacy has run out of pediatric antibiotics.*

*You go home empty-handed, out of money, with a sick child.*

*This is the 'Wasted Trip Dilemma.' It happens millions of times every year across rural India. Healthcare apps built for urban tech workers assume doctors are always sitting in their offices and pharmacies are always stocked. That is simply not the rural reality."*

---

### [0:40 – 1:30] The Solution: What is NALAM AI?

*"Meet **NALAM AI** — our AI-powered rural healthcare accessibility and coordination platform.*

*Our tagline is our promise: **No Wasted Trips. Better Access. Continuous Care.***

*NALAM AI bridges this gap through two critical breakthroughs:*

*First, **Uncertainty-Aware Trip Routing.** NALAM AI doesn't just tell you the closest clinic. It evaluates doctor presence, and computes probabilistic medicine stock availability from frontline ASHA and staff reports.*

*Then, using an **Expected Loss Algorithm**, it calculates the risk of a wasted trip:  
$\text{Expected Loss} = \text{Failure Probability} \times \text{Travel Distance}$.*

*If the clinic 2 kilometers away has an 80% chance of being out of stock, NALAM AI safely routes you to the Community Health Centre 5 kilometers away where stock is confirmed LIKELY—saving you hours of suffering and a wasted trip."*

---

### [1:30 – 2:20] Live Demonstration: Dual Modality & Inclusive Access

*(Switch to screen demo)*

*"Second, **Universal Accessibility.** Notice our web application:*
- *It is **Tamil-first**, fully localized, responsive, and designed for low-bandwidth rural networks.*
- *Notice the patient consent:* privacy defaults to **False**—no medical record is exposed without explicit patient opt-in.
- *Notice the doctor attendance:* attendance is marked **PRESENT** only when the doctor physically logs in from their verified account.

*But what about the 40% of rural villagers who do NOT own a smartphone?*

*(Show the IVR Terminal Simulator)*

*NALAM AI works seamlessly over ordinary 2G button phones. By dialing our IVR service, any villager can navigate in spoken Tamil or English using their telephone keypad: check doctor shifts, check medicine availability, and book confirmed appointment slots—with zero internet dependency."*

---

### [2:20 – 3:00] Impact & Conclusion

*"Judges, NALAM AI has been fully engineered and tested:*
- *134 automated unit, security, integration, and E2E tests.*
- *Strict non-diagnostic boundaries: we coordinate access, leaving medical diagnosis to licensed doctors.*
- *Zero double-booking through partial database unique constraints.*

*Healthcare access shouldn't depend on luck, and it shouldn't depend on owning an expensive smartphone.*

*With NALAM AI, we ensure: **No Wasted Trips. Better Access. Continuous Care.***

*Thank you, and we welcome your questions!"*
