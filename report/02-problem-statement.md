# 2. Problem Statement and Business Case

## 2.1 Problem Definition

The problem can be stated as a single compound requirement that current tooling does not satisfy:

> An organisation needs to convert an unstructured résumé into a complete, correctly-scoped onboarding plan; to validate and route leave requests against written policy up to a human decision; and to answer employee policy questions grounded in the organisation's own documents — while ensuring that no employee, manager, or HR administrator can see or act on data outside their remit.

Decomposed, four distinct failures are present in the baseline process this project inherits:

**P1 — Transcription loss and error.** Résumé data is manually re-keyed into an HR system. Any field transcribed by hand is a candidate for error, and the original document and the system of record drift apart permanently.

**P2 — Checklist generation is a manual, expertise-dependent task.** The onboarding plan for a new Data Engineer is not the same as for a Designer. Drafting the right checklist requires knowing both the role and the organisation's standard practice, and it is usually done by one experienced person at speed, making it inconsistent and non-repeatable.

**P3 — Scheduling is a negotiation bottleneck.** Booking the required introductory meetings requires checking availability across several calendars while respecting working hours, lunch breaks, and existing commitments. This is mechanical work that consumes a coordinator's attention and still produces conflicts.

**P4 — Policy application is unauditable and inconsistent.** Leave rules — balance sufficiency, approval thresholds, notice periods — exist as documents. They are applied from memory. A manager can reject a valid request, or approve one the policy forbids, and neither error is detectable from the system afterwards because the system holds no record of the rule that was applied or the authority that decided.

A fifth weakness underlies all four, and is easy to overlook because it is not a process failure:

**P5 — There is no access control.** In a system where every authenticated user reaches every employee's record, confidentiality does not depend on discipline. A departing employee's full file, an unuploaded résumé, and a manager's leave history are all equally visible to everyone. Any assessment of the first four problems is incomplete without addressing this, because the remediation itself introduces new exposure.

## 2.2 Business and Real-World Context

These are not hypothetical problems. They are the ordinary state of onboarding at organisations that have not invested in integrated tooling, which includes a large share of small and mid-sized firms where the HR function is one or two people.

**The cost of manual onboarding.** Industry estimates consistently place the administrative cost of onboarding a single employee in the range of roughly £1,000–£3,000 when manager time is included, and a 3–6 week span of calendar time from offer accepted to productive. The larger cost is indirect: a new hire who lacks a working laptop, an account, or a named owner in week one spends that week unable to contribute at all.

**The cost of leave-policy inconsistency.** Manual approval means the policy is enforced only as consistently as the approver remembers it. In a multi-team organisation this produces measurably uneven outcomes between employees doing comparable work, and the resulting fairness complaints are disproportionately about process rather than substance. It also creates a records problem: without an immutable decision log, a disputed outcome cannot be resolved.

**The regulatory dimension.** Several jurisdictions treat employee records as personal data subject to access, retention, and breach-notification rules. A system where every user can read every record increases breach exposure by widening the number of parties who can cause one, and complicates any data-subject access request because there is no principled definition of who should have seen what.

**The strategic dimension.** Organisations that automate onboarding measurably improve time-to-productivity, and the effect is largest in roles where the onboarding path is well-defined. This is the case this system targets. The commercial argument is not cost reduction in the HR team alone; it is that a fast, consistent, and visible first month measurably improves early retention.

## 2.3 Business Case for Automation

Aggregating the addressable problems, the case has four parts. Each is expressed as a mechanism rather than a percentage, because honest automation business cases are mechanism-based — the savings come from a specific activity becoming cheaper or impossible to skip, and the magnitude depends on headcount and attrition that this project cannot know.

| Problem | Addressed by | Mechanism of benefit |
|---|---|---|
| P1 Transcription | Resume Agent → deterministic record creation | Eliminates re-keying entirely for the document-derived fields; the résumé becomes the system of record. |
| P2 Checklist | Onboarding Agent, template-based on role + department | Removes the expertise bottleneck. A fresher onboarding no longer depends on which manager drafts it. |
| P3 Scheduling | Calendar Agent, deterministic slot finding | Removes the negotiation loop; conflicts and working-hour violations are prevented by construction. |
| P4 Policy application | Leave Agent + Policy/RAG Agent, with an attributable decision log | Converts an unauditable memory-based decision into a rule-based one with a named decider and a persisted reason. |
| P5 Access control | Role-based authorisation on every request and every query | Reduces breach surface from "every authenticated user" to "the people who need the record." |

The strongest return is on P1–P3, which are pure manual effort. P4 and P5 are risk-reduction plays: individually less visible, but they are the failures that produce a compliance incident or an unfairness complaint rather than a slow week, and they are the reason the system cannot be considered a success on throughput metrics alone.
