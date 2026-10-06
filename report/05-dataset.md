# 5. Dataset and Knowledge Sources

## 5.1 Knowledge Base: HR Policy Corpus

The system's RAG component is grounded in a corpus of five policy documents, authored for this project and committed to the repository at `backend/data/policies/`.

| Document | Size | Domain covered |
|---|---|---|
| `leave_policy.txt` | 1,553 B | Casual/sick/earned leave entitlements, auto-approval threshold, carry-forward, notice periods |
| `security_policy.txt` | 1,553 B | Password policy, data handling, device and access requirements |
| `onboarding_policy.txt` | 1,287 B | First-week checklist, document requirements, buddy and induction responsibilities |
| `work_from_home_policy.txt` | 1,220 B | WFH eligibility, weekly allowance, approval and equipment conditions |
| `attendance_policy.txt` | 1,023 B | Working hours, lunch break, late-login and absence handling |

**Total: 6,636 bytes across 5 documents.**

This corpus is small, and the report should be candid about what that means. A five-document corpus is appropriate for demonstrating the *retrieval architecture* and for measuring whether the grounding behaviour works, but it is two to three orders of magnitude smaller than a real HR handbook. Every retrieval metric in Section 11 is reported against this corpus and **must not be read as a performance claim about production-scale retrieval.** The honest claim is narrower: the pipeline retrieves the correct document for an answerable question, and refuses the ones it cannot support. Scaling the corpus is discussed in Section 13.

The documents were authored to be *representative* rather than trivially easy: they contain specific numbers (entitlement days, the auto-approval threshold, working hours) that a retrieval system must surface accurately, because these are the facts on which real decisions depend. A corpus of vague prose would not test the system.

## 5.2 Operational Data: Seeded Demonstration Dataset

The prototype ships with a seeded relational dataset so that the system is demonstrable immediately on first run, without requiring the user to upload résumés before anything is visible.

| Entity | Rows | Composition |
|---|---|---|
| Employees | 7 | 2 managers, 4 employees, 1 HR; 3 departments |
| Login accounts | 7 | One per employee; roles derived from the email-prefix policy |
| Onboarding tasks | 70 | 10 per employee, role/department-specific |
| Meetings | 9 | Introductory meetings across work hours |
| Leave requests | 4 | 2 pending (requiring approval), 1 approved, 1 rejected |
| Leave balances | 21 | 3 leave types × 7 employees |
| Agent log rows | 19 | Seed provenance and workflow history |

Task statuses are deliberately non-uniform: **46 COMPLETED, 13 TODO, 11 OVERDUE.** This is not decoration. A prototype in which every task is complete cannot demonstrate progress tracking, and the employee dashboard's progress calculation is untestable against uniform data. The distribution exists so that the progress and overdue-counting logic has something real to compute.

The org hierarchy is a real structure, not a flat list, because access control is scope-dependent: Priya Sharma manages Arun Kumar, Vikram Singh, and Daniel Fernandes; Anil Menon manages Sneha Patel; Meera Iyer is HR. This is what makes the manager isolation tests in Section 11 meaningful — there must exist an employee outside a given manager's scope for the isolation assertion to have any content.

## 5.3 Evaluation Query Set

For the retrieval evaluation in Section 11.3, a labelled query set was constructed, and each query was classified against the corpus by **grep-verified search of the policy files rather than by assumption.** This distinction mattered: an initial version of the evaluation set contained "Do I get a free lunch?" in the out-of-corpus category, but the attendance policy does specify a one-hour lunch break, so the query was answerable and its apparent failure was a mislabelled test, not a system defect. The corrected figures are the ones reported.

| Category | n | Purpose | Correct behaviour |
|---|---|---|---|
| **Answerable** | 14 | Questions whose answer is in the corpus | Retrieve the chunk containing the answer |
| **Unanswerable** | 6 | Topics verified absent by grep (dress code, gym reimbursement, free lunch allowance, remote stipend, maternity leave, parking) | Return no grounding; refuse to answer |

The unanswerable set matters as much as the answerable one. A RAG system that answers every question will always score well on recall; the property that distinguishes a grounded system from a plausible one is whether it declines to answer when the corpus cannot support an answer. The 6 unanswerable queries are drawn from topics an employee plausibly *would* ask, so a system that confabulates from model priors would fail them.

## 5.4 Résumé Inputs

The résumé-ingestion path is designed to accept arbitrary PDF uploads, and the system creates the employee record, task plan, and meetings from them. For reproducible evaluation, the repository does not include third-party résumés, since they are personal data that should not be redistributed. Evaluation of the extraction path was therefore performed with synthetic documents containing the same structural conventions as real résumés — name, contact block, section headings, experience entries with date ranges, education, and a skills list — and the extraction heuristics were checked against both formats.

This is a genuine limitation of the evaluation and is reported as such in Section 11: extraction accuracy figures come from synthetic and heuristic checks, not from a corpus of real résumés with known ground truth, and no claim is made about accuracy on arbitrary real-world PDF layouts.
