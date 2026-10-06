# 13. Future Enhancements and Conclusion

## 13.1 Roadmap

Prioritised by what blocks a real deployment, not by what is most interesting to build. The ordering matters: items R1–R3 are prerequisites for any use beyond a local demonstration.

### Priority 1 — Required before deployment

| # | Item | Rationale | Effort |
|---|---|---|---|
| R1 | **Configure a supported embedding model** and rebuild the index | Closes L1, the system's only outright technical failure. Fixes the known paraphrase weakness (L1) and allows a real semantic-retrieval benchmark. Configurable via env, already — only the model identifier and credentials are missing. | S |
| R2 | **Expand the policy corpus** to the full handbook, with chunking re-tuned at the new size | L2. All current retrieval figures are corpus-specific and must be re-measured. Adds the two unindexed policy types. | M |
| R3 | **Remove or authenticate `POST /api/auth/demo-accounts`** | L8. Currently discloses seeded names, emails, and roles to any caller. One-line change: gate it behind `DEBUG` or the HR role. | XS |
| R4 | **Migrate SQLite → PostgreSQL** with Alembic migrations | L10. Required for concurrent access beyond a single process. The ORM layer is portable by design, so this is a URL change plus a migration baseline. | M |

### Priority 2 — Required for the product to be usable

| # | Item | Rationale | Effort |
|---|---|---|---|
| R5 | **Approval notifications** — email and/or Slack, on request creation, on decision, and on a pending-request digest | L9. The largest product gap. An approver who must remember to check a queue will approve late or not at all, and the system's value is bounded by approval latency. | M |
| R6 | **An HR endpoint to adjust leave balances** (grant, correct, carry forward) | The seed bug is fixed, but entitlement is still only set at hire. The policy's carry-forward rule (earned leave up to 30 days) and year-end lapse are documented and unenforced. | S |
| R7 | **Replace error-text matching with typed error codes** | L7. Introduce `error_code` in graph state (`DUPLICATE_EMPLOYEE`, `INSUFFICIENT_BALANCE`, `VALIDATION_ERROR`) and route on that. Removes the last fragile coupling in the orchestration layer. | S |
| R8 | **Task reminders and escalation** for overdue items, wired to notifications | 11 of 70 seeded tasks are deliberately `OVERDUE`. Without reminders, the dashboard reports a problem nobody is told about. | M |
| R9 | **Delete-on-request and data-retention policy** | A documented GDPR/retention path for employee records and résumés. Required for a real personal-data deployment. | M |

### Priority 3 — Extends capability

| # | Item | Rationale | Effort |
|---|---|---|---|
| R10 | **Résumé layout robustness** — column and table-aware extraction, an evaluation set of real (redacted) résumés | L5. Turns an unmeasured path into a measured one. | L |
| R11 | **Meeting rescheduling and cancellation**, with attendee notification | The calendar agent schedules but cannot adapt when a new hire's start date moves, which is common. | M |
| R12 | **Delegation and out-of-office approver substitution** | A manager on leave creates a deadlock: their reports' requests cannot be approved. Real and currently unhandled. | M |
| R13 | **Multi-tenant support** — organisation scoping on every table | Every current authorisation rule assumes one organisation. The HR role is, in effect, a tenant administrator. | L |
| R14 | **Richer workflow: probation review, equipment lifecycle, training plan** | Extends the template mechanism that already generalises across role and department. | M |
| R15 | **Evaluation harness in CI** — the RBAC matrix, isolation checks, and a versioned labelled query set, run on every commit | Prevents the class of regression in R3/R10 that produced the `decided_by` bug. Makes access control a continuously enforced property. | M |
| R16 | **Per-query retrieval tracing** — record which chunks answered which question, with scores, in `agent_logs` | Makes a wrong answer debuggable after the fact instead of speculatively. Directly addresses L2's observability problem. | S |

### Explicitly out of scope

Recruitment and candidate ranking, payroll, performance management, and disciplinary procedure. These carry materially different fairness and regulatory obligations than onboarding administration, and automating them would require a different and much more rigorous evidential standard than the one applied here.

## 13.2 Long-Term Vision

The immediate roadmap is engineering hygiene. The longer question is what the architecture becomes if the template mechanism is generalised properly.

**From workflow automation to an onboarding knowledge graph.** The system currently represents the relationship between role, department, and required onboarding steps as a template lookup. Generalised, those templates are edges in a graph over roles, tasks, systems, and equipment. The valuable property is not automation — it is that the *organisation's own structure* becomes machine-readable, and the AI's job becomes to propose and maintain that structure rather than to be a black box inside it.

**From answering questions to anticipating them.** The system answers what an employee asks. A system that observed the 70 tasks generated for new hires, and the patterns in what employees actually query, could identify onboarding steps the organisation has not formalised — a gap where new hires repeatedly ask the same unanswered question is a documentation defect the system can locate.

**From single-organisation to evidence.** Because every action is attributed and every rule application is deterministic, the system produces something scarce: a record of how policy was actually applied over time, not just what the policy says. That is the kind of artefact that supports an audit without reconstructing one.

**A caution about the trajectory.** Each of these steps moves the system closer to making judgements about people — about what a role requires, about what a person needs, about who should be hired. The constraint established in this project, that reproducible decisions are excluded from the model and attributed to a named human, is what makes the current system defensible. It should be treated as a fixed boundary, not a starting position to be relaxed as the system gets smarter. The failure mode of agentic HR systems is not that the model is too weak; it is that a probabilistic component is allowed to make a consequential decision and the surrounding system is confident enough to hide the fact.

## 13.3 Conclusion

This project built a working agentic system for employee onboarding: five specialised agents coordinated by a supervisor, a LangGraph workflow with genuine human-in-the-loop leave approval, a grounded policy retrieval layer, and role-based access control verified by 38 automated assertions and 10 cross-scope leakage checks — all passing.

The finding worth carrying forward is not the agent architecture itself, which is now a commodity. It is the discipline of **knowing precisely where the model belongs**. The system uses a model to read a résumé and to interpret a free-text request, and uses code to decide what happens next. That boundary is what makes the leave ledger reproducible, made the 1–3 ms deterministic endpoints possible, and — when the interrupt payload dropped the approver's identity and the audit trail silently recorded "HR Admin" for every approval — the discipline is also what made the bug findable, because the system was supposed to be attributing decisions and visibly was not.

The project also produced an honest account of its own weaknesses, which is the more useful half. The embedding model is unavailable, so the semantic retrieval path — the architecturally preferred one — does not execute, and the measured 85.7% recall describes a keyword fallback on a 6.6 KB corpus, not a production retrieval system. Two of five policy types are not even indexed. The dataset is seven employees, so the latency figures are evidence of cheapness and not of scalability. No user study was run, so every claim about time saved and adoption is a mechanism argument, not a measurement. The most instructive failure was the zero-balance seed, which made the entire leave workflow unusable while the test suite stayed green, because the suite only asserted the rejection path and a zero balance makes rejection the *only* reachable outcome. It was caught by rereading the policy document and asking why a documented auto-approval rule could never execute. None of these is disqualifying for a prototype; all of them are disqualifying if presented as more than a prototype.

The system is therefore what it should be at this stage: functionally complete, access-controlled, reproducible, and measured against itself rather than against an aspiration. The remaining work is well specified, and the first three items on the roadmap — a working embedding model, a real policy corpus, and closing the demo-accounts endpoint — are the difference between a demonstration and something that could be deployed.
