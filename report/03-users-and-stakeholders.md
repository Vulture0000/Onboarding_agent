# 3. User and Stakeholder Analysis

## 3.1 Target Users

The system serves three roles, distinguished by what they need to *do* rather than by their seniority. Each is a primary persona with distinct goals, constraints, and failure modes.

### Persona 1 — The New Hire (Employee)

**Profile.** Joined in the last 30 days. Often still forming an understanding of how the organisation actually works. Has no prior context, and therefore no ability to judge whether an answer they receive is correct.

**Goals.** To know what to do, in what order, and by when. To understand what is permitted before they need it. To not have to ask basic questions that make them look inattentive.

**Constraints.** Low context, so an error is expensive and invisible. Cannot evaluate the answer's correctness, meaning a wrong answer is more damaging to them than no answer.

**Failure mode if the system fails.** They receive a partial plan, or a policy answer that is confidently wrong, and they act on it. Because they cannot detect the error, the failure propagates silently into their first month.

**Design implication.** The employee view is deliberately narrow. It exposes only the signed-in user's own records, and it shows progress explicitly. It answers from retrieved policy text rather than from a model's general knowledge, because an employee has no way to distinguish a grounded answer from a plausible fabrication.

### Persona 2 — The Team Manager

**Profile.** Manages 3–8 people. Responsible for their output and for approving their time off. Understands their own team's process well and the wider organisation poorly.

**Goals.** To see at a glance who is behind and why. To decide leave requests quickly and with confidence that the decision is correct and defensible. To not be exposed to other teams' data.

**Constraints.** Time-constrained and interruption-driven; will not read a long document to approve a request. Needs the decision's basis at the point of decision.

**Failure mode if the system fails.** They either approve blind (accepting whatever arrives, so the human check becomes theatre) or they investigate manually by asking HR, which reinstates the bottleneck the system was meant to remove.

**Design implication.** The manager's queue is scoped to direct reports. Every decision request displays the rule that applies and the balance that will result. The system never approves on their behalf; it removes the work that made approval feel burdensome.

### Persona 3 — The HR Administrator

**Profile.** Owns the employee master data and the policy corpus. The only role with organisation-wide visibility. Accountable for both accuracy and confidentiality.

**Goals.** To onboard someone quickly without typing their details. To trust that the policy documents and the system's behaviour have not diverged. To be confident that data is not leaking across roles.

**Constraints.** Small in number, so a process change that only helps one person at a time has poor leverage — but a process that risks their accountability has immediate negative leverage.

**Failure mode if the system fails.** They lose confidence in the automation and revert to manual, which is worse than never having automated: the data now exists in two systems and neither can be trusted.

**Design implication.** HR sees the reasoning behind every automated action in an activity feed, and the access-control matrix is treated as a testable property rather than an assumption.

## 3.2 Stakeholder Identification

Beyond the three direct users, four stakeholder groups have an interest and are affected by design decisions.

| Stakeholder | Interest | Affected by | How the design accounts for them |
|---|---|---|---|
| **Prospective hires** | Judgement of the organisation; speed of offer-to-start | Whether the visible first week looks organised and human | Self-service view with progress visibility; new hire reaches a working state without depending on coordinator availability |
| **IT / Facilities** | Asset and access provisioning accuracy | Data the onboarding agent produces drives their queue | Task plan is the provisioning instruction; deterministic templates mean the same role always yields the same tasks |
| **Compliance / Data Protection** | Access control, auditability, retention | Every read of an employee record | Role scoping on every query; every decision and agent action persisted with an attributable actor; scope verified by automated tests |
| **The organisation's leadership** | Time-to-productivity, retention, consistency | Aggregate outcomes | Dashboard statistics; standardisation of the onboarding path across roles |

**A note on the IT/Facilities stakeholder, which is easy to overlook.** The onboarding task list is not merely a checklist for the new hire; it is the provisioning request for every other team. A task list that is inconsistent for the same role generates duplicate or missing access requests. This is a concrete reason the task plan is template-driven and deterministic rather than model-generated per hire — determinism here is a benefit to a third party, not just an engineering preference.

## 3.3 User Requirements

Requirements are separated by verification method, because the distinction determines what evidence Section 11 can present. Requirements R1–R7 are **functional** and verified by executing the system; R8–R12 are **non-functional** and are verified either by automated assertion or by design inspection, which this report states explicitly rather than implying all requirements were equally tested.

| ID | Requirement | Pri | Verification |
|---|---|---|---|
| R1 | A résumé upload produces an employee record, a task plan, and scheduled meetings without manual steps | Must | Functional test of the full workflow |
| R2 | Task plans are role- and department-specific, not generic | Must | Functional: distinct plans for distinct roles |
| R3 | Meetings respect working hours, lunch breaks, and existing commitments | Must | Functional: conflict and hour assertions |
| R4 | A leave request is validated against balance and policy before it is decided | Must | Functional: insufficient balance → rejection |
| R5 | A request requiring approval pauses, is decided by a named human, and records who decided it and why | Must | Functional: interrupt/resume, attributed decision |
| R6 | Requests within the auto-approval limit are approved without human involvement | Must | Functional: short SICK request auto-approves |
| R7 | Policy answers quote the organisation's documents; out-of-corpus questions are refused | Must | Functional: retrieval-hit and refusal tests |
| R8 | An employee reaches only their own records | Must | Automated RBAC matrix (401/403/200 assertions) |
| R9 | A manager reaches their reports and not other teams | Must | Automated isolation tests |
| R10 | HR-only functions are unreachable for other roles, including at the API level | Must | Automated negative tests |
| R11 | The core system functions with no LLM API key configured | Should | Functional: graceful-degradation test |
| R12 | Every automated action is logged with an attributable actor | Should | Design inspection of `agent_logs` |
| R13 | A new user can self-register, is signed in automatically, and lands on a usable account with a generated onboarding plan | Must | Functional: browser end-to-end signup |
| R14 | Self-registration cannot grant MANAGER or HR, whatever the client sends | Must | Automated: role field absent from the schema; escalation attempt returns EMPLOYEE |
| R15 | Signup with an email HR already created links to that record rather than creating a duplicate | Must | Functional: row count before/after |

**Requirement R10 deserves emphasis.** "Unreachable at the API level" is distinct from "not linked in the navigation". A hidden navigation item is not a security control — it is a usability convention that any user with browser developer tools can bypass. The implementation therefore enforces authorisation on the server for every request, and the test suite asserts the 403 responses directly. The frontend guards exist for user experience; they are not the security boundary, and R10 is defined so that the tests pass if the frontend were removed entirely.
