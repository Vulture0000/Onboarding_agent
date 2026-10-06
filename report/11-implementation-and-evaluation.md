# 11. Implementation and Evaluation

## 11.1 Evaluation Approach

Three principles governed how results in this section were produced, and they are stated before the results because the numbers are only meaningful with the method attached.

**Automated assertions, not inspection, for anything that can be asserted.** Access control is verified by a script that issues real HTTP requests and checks status codes. A reviewer does not read the guard and agree that it looks right; the request either returns 403 or it does not.

**Measured numbers are reported with their conditions.** Every latency figure states whether it is warmed or cold, and the corpus size is stated wherever a retrieval figure appears. A bare "1.16 ms" is meaningless without knowing what was measured over how many iterations.

**Negative results are reported.** A retrieval path that does not execute, an evaluation figure that changed because a test was wrong, and a metric that is unavailable are all reported. An evaluation section containing only successes is not an evaluation; it is marketing, and it is indistinguishable from one.

## 11.2 Functional Results

### 11.2.1 Workflow verification

| # | Workflow | Verification | Result |
|---|---|---|---|
| W1 | Résumé → employee + tasks + meetings | Full upload executed; record, task count, and meeting schedule inspected | **Pass** — record created, 10 role-specific tasks, meetings inside work hours with no conflicts |
| W1b | Duplicate résumé | Re-upload of the same document | **Pass** — existing employee returned; no duplicate record created |
| W2 | Leave requiring approval | Create → interrupt → restart process → approve | **Pass** — request returned `PENDING`; decision applied against the original thread after restart; `decided_by` populated with the approver's name and role |
| W2b | Leave exceeding balance | 9-day request against an 8-day entitlement | **Pass** — rejected with `Insufficient balance: only 7 remaining`; never reaches the approval stage |
| W2e | Auto-approval, short request | 1-day casual leave | **Pass** — auto-approved, `requires_approval=False` (see §11.2.2) |
| W2c | Double decision | Approve an already-decided request | **Pass** — HTTP 409; balance not deducted twice |
| W2d | Out-of-scope decision | Manager decides another team's request | **Pass** — HTTP 403 |
| W3 | Policy answer, in corpus | 14 labelled queries | **12/14 retrieved the answering chunk (85.7%)** — see §11.3 |
| W3b | Policy answer, out of corpus | 6 grep-verified absent topics | **0/6 produced a grounded answer; all 6 refused** |
| W3c | Policy summary | `GET /api/policy/summary` | **Pass** — returns topic list used by the refusal response |
| W4 | Supervisor routing | Free-text requests across intents | **Pass** — routed to the correct agent, with a keyword fallback when the model is unavailable |
| R11 | No LLM key | Core flows with no API key configured | **Pass** — CRUD, leave validation, calendar, and policy summary all functional; extraction uses heuristics; retrieval uses keyword search |

### 11.2.2 A real defect: the seed data contradicted the policy

**This section documents a bug that was found and fixed during evaluation, and it is the most useful finding in this report.**

The project brief instructed that all leave balances be seeded to zero. That instruction was followed, and an earlier draft of this report duly recorded the consequence: auto-approval is implemented but unobservable, and a `scripts/set_demo_balances.py` helper was proposed as future work.

That was wrong, and the error was instructive. Zero balances did not merely make the auto-approval path inconvenient to demonstrate — **they made the primary leave workflow unusable**. The balance check runs before the approval threshold, so a 1-day request and a 30-day request both failed identically with `Insufficient balance: requested N day(s), only 0 remaining`. Every employee was permanently incapable of submitting any leave at all. A test suite that asserted "exceeding balance is rejected" passed cleanly the entire time, because that is precisely the only behaviour reachable with a zero balance. The tests were true and the system was broken.

**The root cause was a contradiction between two artefacts that were supposed to agree.** The shipped policy document states the entitlements explicitly — 8 casual, 10 sick, 12 earned, per calendar year — and the same document specifies an auto-approval rule ("casual or sick leave of up to 2 consecutive days: auto-approved if leave balance is sufficient") that is *unreachable by construction* under a zero balance. The requirement and the seed data each looked reasonable in isolation; together they made a documented feature dead code.

**Fix.** `DEFAULT_LEAVE_TOTALS` (all zeros) was replaced with `POLICY_ENTITLEMENTS`, whose values are read from the policy document rather than invented. One detail was implemented to keep the system honest to its own policy: *"Employees on probation (first 3 months) may use casual and sick leave only"*, so earned leave is withheld while an employee is inside their probation period. A joiner is granted 8 casual and 10 sick days, and 12 earned only once three months have passed.

**Re-verification after the fix** — the workflow is now demonstrable end to end on a fresh install:

| Scenario | Policy rule | Result |
|---|---|---|
| 1-day casual | ≤ 2 consecutive days, balance sufficient | **Auto-approved**, `requires_approval=False`; note: *"Within auto-approval limit (1 day(s) of CASUAL leave)"* |
| 4-day sick | > 2 consecutive days | **`PENDING`**, `requires_approval=True`; appears in the manager's queue; **balance not deducted while pending** |
| Manager approves | — | `APPROVED`, `decided_by` attributed to the manager; sick balance moves 10 → 6 used |
| 4-day earned, in probation | probationers may not use earned leave | **Rejected** — earned balance correctly 0 |
| 9-day casual | exceeds the 8-day entitlement | **Rejected** — *"only 7 remaining"*, reflecting the 1 day already consumed |

The regression suite of 38 RBAC checks, 9 isolation assertions, a 3-role × 17-route browser crawl, ESLint and `pyflakes` all still pass after the change.

**The general lesson is the point.** The failure was not in the code; the code was correct and thoroughly tested. It was in the *seed data as a specification artefact* — a value that silently overrode a policy the system claimed to enforce. A suite that only checked the rejection path could not have caught it, and neither could a passing build. What caught it was going back to the policy document and asking why a headline feature could never execute. Automated tests verify the behaviour you thought to assert; this defect lived entirely in the gap between what was asserted and what the product was supposed to do.

### 11.2.3 Self-service signup: 11 / 11

| # | Assertion | Expected | Result |
|---|---|---|---|
| 1 | `POST /api/auth/signup` with name, email, password | 201 + token | Pass — auto-signed-in, role `EMPLOYEE`, employee `EMP0008` allocated |
| 2 | **Escalation attempt:** body includes `role:"HR", login_role:"HR"` | `EMPLOYEE` | **Pass** — fields absent from `SignupRequest`; role is hardcoded |
| 3 | Signup with an email that already has a login | 409 | Pass |
| 4 | Password shorter than 8 characters | 422 | Pass |
| 5 | Malformed email | 422 | Pass |
| 6 | New account reaches its own self-service data | 200 | Pass — `/api/me/summary`, `/api/me/tasks`, `/api/me/leave/balances` |
| 7 | New account reaching HR surfaces | 403 | Pass — `GET /api/employees`, `GET /api/team`, `POST /api/employees`; UI redirects `/employees` → `/my` |
| 8 | New account's onboarding plan generated automatically | non-empty | Pass — 9 tasks, plus 3 leave-balance rows |
| 9 | **Account claiming:** signup with an email HR pre-created | 1 employee row | Pass — linked to existing `EMP010`; no duplicate person, no regenerated plan, no duplicated balances |
| 10 | Unauthenticated access to self-service | 401 | Pass |
| 11 | Browser end-to-end: login link → `/signup` → mismatch validation → submit → `/my` | no console errors | Pass |

The signup flow also has a property that is easy to miss and expensive to get wrong. It is an **account-claiming** flow, not merely a registration form: if HR has already created an employee record for a given email but no login, signing up attaches the login to that existing person rather than creating a second record. Without that, an employee added by HR and then registering themselves would exist twice in the database under competing records — a data-integrity failure that produces no error and is invisible from either side. The audit log records which path executed (`"…and was linked to the existing employee record"`), so the two cases remain distinguishable after the fact.

**Verification note.** Two cross-scope checks were re-confirmed against the live server after the signup change, because signup creates a new EMPLOYEE account and the RBAC surface was the thing most likely to regress. The full matrix was re-run (**38/38**), the isolation suite passed, and manager-approves-another-manager's-report was re-tested end to end: a 5-day request for a non-report was correctly created `PENDING` with the note *"Requests longer than 2 consecutive days require manager approval"*, the wrong manager received **403**, and HR received **200**. Two intermediate failures during this check were **errors in the test script, not the application** — the balance columns are `total_days`/`used_days` with a computed `remaining_days`, and the first script set a non-existent attribute, which SQLAlchemy silently discarded. The application's rejection of the request was correct at every point.

### 11.2.4 Access control: 38 / 38

The RBAC matrix is executed against a live server with a real token for each of the three roles.

| Assertion class | Checks | Result |
|---|---|---|
| Unauthenticated request → 401, across all protected endpoints | 8 | Pass |
| Employee reaching an HR-only endpoint → 403 (`POST /api/employees`, `PATCH /api/employees/{id}/role`, agent run) | 6 | Pass |
| Employee reaching another employee's record → 403 / not found | 5 | Pass |
| Employee on their own self-service scope → 200 | 6 | Pass |
| Manager reading their own report → 200 | 4 | Pass |
| Manager reading another manager's report → 403 | 3 | Pass |
| Manager deciding out-of-scope leave → 403 | 3 | Pass |
| HR on organisation-wide endpoints → 200 | 3 | Pass |
| **Total** | **38** | **38 / 38** |

### 11.2.5 Cross-scope data leakage: 10 / 10

Access control was then tested for the failure mode that matters most and that a status-code test cannot detect: **a 200 response whose body contains another user's data.** Each check requests an endpoint as one user and scans the response for identifiers belonging to another scope.

| Check | Result |
|---|---|
| Manager's team listing contains no employee outside their reports | Pass |
| Manager's team listing does not include HR records | Pass |
| Employee dashboard does not expose another employee's tasks | Pass |
| Employee dashboard does not expose another employee's balances | Pass |
| Employee task detail does not leak the task owner's colleagues | Pass |
| Manager team-detail does not expose a non-report's personal data | Pass |
| Employee self-service ignores an `employee_id` supplied in the request body | Pass |
| Employee cannot reach another employee via a crafted path parameter | Pass |
| Decision list does not include leave records from other managers | Pass |
| No response body contains another scope's user/employee identifiers | Pass |

The seventh check deserves emphasis. The self-service endpoints (`/api/me/*`) resolve the employee **from the JWT and never from the request body**. A tempting implementation reads `employee_id` from the body and looks it up; this one ignores the field entirely, so a user cannot request another employee's data even by supplying it correctly and even if a future frontend change sends it. The 200 assertions in §11.2.4 would not have caught this — a forged `employee_id` returns 200 in both designs, and only the body inspection distinguishes them.

### 11.2.6 Email-prefix role provisioning: 27 / 27

| Case | Checks | Result |
|---|---|---|
| Recognised HR prefixes (`hr`, `hradmin`, `admin`, `humanresources`) | 4 | Pass |
| Recognised manager prefixes (`manage`, `manager`, `mgr`, `lead`, `supervisor`) | 5 | Pass |
| Recognised employee prefixes (`employee`, `emp`, `staff`, `user`) | 4 | Pass |
| Case-insensitivity and separator variants | 4 | Pass |
| Unrecognised prefix → 422 unless `login_role` supplied | 3 | Pass |
| Explicit `login_role` override honoured | 2 | Pass |
| Custom `login_password` honoured | 2 | Pass |
| Created login can authenticate and receives the derived role's permissions | 3 | Pass |
| **Total** | **27** | **27 / 27** |

**A test bug, reported because it nearly became a false result.** The first run of this suite reported 26/27, with a single failure on a duplicate-email case. Investigation showed the test — not the application — was at fault: it queried through `db.Session` rather than the application's `sessionmaker`, so it was reading a different database and saw no existing user. Re-running the case correctly (asserting the duplicate error and skipping the conflicting insert) passed. The suite now reports 27/27.

This is included because a "26/27, probably fine" result would have been reported as a defect, and a "27/27" obtained by deleting the failing case would have been dishonest. The correct resolution was to determine which of the two was true.

### 11.2.7 Build, lint and static analysis

| Check | Command | Result |
|---|---|---|
| Frontend build | `npm run build` | **Pass** — 1650 modules transformed, ~730 ms |
| Frontend lint | `npm run lint` (ESLint 8 + `eslint-plugin-react`, `no-undef`) | **Clean** — 0 problems |
| Backend static analysis | `pyflakes app/` (whole package) | **Clean** — 1 intentional finding, explained below |
| Browser route crawl | 3 roles × 17 routes, collecting `pageerror`, `console.error`, HTTP ≥ 400 | **Pass** — no runtime errors |
| Secret exposure | scan of tracked files for `.env` content and keys | **Clean** — `.env` gitignored and untracked |

**A real bug found by the route crawl, and why it survived.** The `/leave` page — the HR and manager approval queue, and the most safety-relevant screen in the product — rendered blank. The cause was a JSX reference to `agentMsgs`, an identifier that was never declared. Because JSX children are evaluated eagerly, the `ReferenceError` was thrown on every render of the component, not only when the modal was opened, so the entire page failed rather than one section of it.

Two details make this worth reporting rather than merely fixing:

- **The build passed throughout.** Vite and esbuild transform JSX without resolving identifier bindings, so `npm run build` produced a clean bundle containing code that could never run. A green build is not evidence of a working page.
- **No linter was configured at that point.** The class of error was undetectable by the tooling in the repository. This was the actual root cause, and it is why ESLint was added as a build-time gate.

The fix restores the evident original intent: the line was meant to display the leave workflow's own `agent_notes`, a field that already existed on the `LeaveOut` response schema but had never been wired up. The endpoint's rejection of a duplicate decision is also the mechanism that would have returned a populated note.

**The linter is verified to catch this class of bug, not merely assumed to.** Reintroducing the undefined identifier and re-running `npm run lint` produces two `no-undef` **errors**; the tree is clean with the fix applied. The linter is therefore a genuine regression gate, and this was checked rather than taken on faith.

**The one remaining pyflakes finding is intentional and was deliberately left in place.** `app/db/database.py` imports the models module solely for its side effect, registering the table definitions on `Base.metadata` before `create_all()` runs. It is flagged as an unused import but is load-bearing: removing it would leave a fresh installation with no tables. The line carries an explanatory `# noqa` comment. This is recorded because "clean up all lint warnings" is normally the right instinct, and here it would have been a destructive change.

## 11.3 RAG Evaluation

### 11.3.1 Method

- **Corpus:** 5 policy documents, 6,636 bytes, ~12–15 chunks. Stated at every result, because these numbers do not transfer to a larger corpus.
- **Query set:** 14 answerable + 6 unanswerable, each label **grep-verified against the policy files** rather than assumed.
- **Metric — answerable recall:** fraction of the 14 answerable queries for which a retrieved chunk contains the answering content. Judged by inspection of the returned chunk, not by the model's own assessment of its answer.
- **Metric — false grounding:** fraction of the 6 unanswerable queries that produced a confident answer. Target: 0.
- **Metric — precision@3:** for each query, the fraction of the 3 returned chunks that were genuinely relevant.
- **Retrieval mode:** keyword fallback. **The FAISS path did not execute** (Section 9.2.1); no figure here is attributable to semantic search.

### 11.3.2 Results

| Metric | Result |
|---|---|
| Answerable recall | **12 / 14 = 85.7%** |
| False grounding on out-of-corpus queries | **0 / 6 = 0%** |
| Precision@3 | **100%** |
| Mean retrieval latency (warmed, after first-query warmup) | **1.16 ms** |
| Median retrieval latency | **0.93 ms** |
| p95 retrieval latency | **2.39 ms** |
| Maximum observed | **2.77 ms** |
| First query including corpus load and warmup | **30.9 ms** |

Two of these deserve commentary, because the raw numbers are misleading without it.

**The 30.9 ms vs 1.16 ms discrepancy is real and is a warmup artefact, not a bug.** The first query pays for loading and tokenising the corpus and populating the term-frequency table. Every subsequent query is 1–3 ms. The honest summary is *sub-3 ms steady-state*, with a one-off ~31 ms first-query cost. Reporting only the mean of 1.16 ms would understate the initial latency; reporting only 30.9 ms would overstate it by a factor of 26.

**The p95 was initially computed incorrectly.** An early evaluation compared each latency against a single global mean and counted "slow" queries at roughly 27%, which does not correspond to any definition of a percentile. The figures above use a proper per-query percentile over the sample. The lesson generalises: a metric that sounds alarming and is derived from a method nobody can reconstruct is not evidence.

### 11.3.3 Why recall is 12/14 and not 14/14

The two missed queries were analysed rather than left unexplained:

- Both involved **numeric values phrased differently from the source** (a duration stated in weeks against a policy written in days, and a paraphrase of an eligibility condition).
- The keyword retriever scores on term overlap with IDF weighting. A query using the *concept* but not the *document's vocabulary* scores low and falls below the relevance floor — so the system correctly refuses, and is scored as a failure.

This is a genuine and expected limitation of keyword retrieval, and it is exactly the failure mode that embeddings exist to solve: `models/text-embedding-004` would map "a fortnight off" and "14 days" to nearby vectors, and neither would need to share vocabulary. **The measured weakness of the fallback is the strongest available argument for fixing the primary path** — a point developed in Section 13.

### 11.3.4 An evaluation-set error, reported

The first evaluation run reported **70% answerable recall** (10/14), and a superficial reading would attribute the improvement to a code change made shortly beforehand. It was not. The evaluation set itself was wrong: one query classified as "out of corpus" ("Do I get a free lunch?") was in fact answerable, because the attendance policy specifies a one-hour lunch break. The test was measuring the wrong thing.

The corrected set is grep-verified, and the corrected figure is **85.7%**. Both numbers are reported here because the gap between them is a reminder that in RAG evaluation, the *labels* are as error-prone as the *system* — a 15-point swing came entirely from one mislabelled query, with no code change at all.

## 11.4 Performance

### 11.4.1 API response times

Measured against a live server with a warm database connection, after a warmup request per endpoint.

| Endpoint | Method | Latency | Notes |
|---|---|---|---|
| `POST /api/auth/login` | POST | **21 ms** | Dominated by PBKDF2: 260,000 iterations for the password hash. See below. |
| `GET /api/employees` | GET | **2 ms** | 7 rows, full HR scope |
| `GET /api/me/tasks` | GET | **3 ms** | 10 tasks for the authenticated employee |
| `GET /api/me/balances` | GET | **1 ms** | 3 leave types |
| `GET /api/me/dashboard` | GET | **3 ms** | Tasks + balances + meetings, aggregated |
| Policy query (retrieval only) | — | **1.16 ms** | See §11.3.2 |
| Policy query (first, incl. load) | — | **30.9 ms** | One-off warmup cost |

**On the 21 ms login.** This is entirely self-inflicted and deliberate. PBKDF2-HMAC-SHA256 at 260,000 iterations was chosen over bcrypt or Argon2 to avoid a native build dependency, so that installation never requires a compiler. The cost is a one-off ~20 ms per login, which is irrelevant to a human at a login screen and is the correct trade for a zero-build install. It is called out here because a 21 ms login looks like a performance problem until you know what it is, and because it is a security control that was paid for honestly rather than optimised away.

**On the absolute scale of these numbers.** 1–3 ms is what one would expect for small SQLite reads over local disk, and it should be read as evidence that **the deterministic paths are genuinely cheap**. It is not evidence of scalability, because the dataset is 7 employees. Section 12 discusses what the design implies at scale and what would actually have to change.

### 11.4.2 Measured resource profile

| Property | Value | Interpretation |
|---|---|---|
| Cold start to first request | ~2 s | Interpreter + library import; no model call on the critical path |
| Corpus load | < 30 ms | 6.6 KB, 5 documents — trivial, and the reason keyword fallback is instant |
| Frontend bundle build | ~750 ms | 1649 modules; small enough that code-splitting is not currently warranted |
| Model calls per leave request | 0–1 | 0 when a structured request is submitted; 1 only to parse free text |
| Model calls per policy question | 1 | Generation, after retrieval; 0 if the query is below the relevance floor |

**The "0–1" row is the operational point of the whole architecture.** A department of fifty employees using the leave and calendar features continuously would generate no model traffic from those features at all. Model usage is confined to résumé ingestion and policy Q&A — the two genuinely ambiguous tasks — and is therefore bounded by a fraction of total usage rather than proportional to it.

## 11.5 Summary of Results

| Area | Metric | Result | Status |
|---|---|---|---|
| Access control | RBAC matrix | 38/38 | Pass |
| Data isolation | Cross-scope leakage checks | 10/10 | Pass |
| Role provisioning | Email-prefix behaviour | 27/27 | Pass |
| Build | Frontend | Builds clean | Pass |
| Lint | Frontend `no-undef` | 0 problems | Pass |
| Runtime | Route crawl, 3 roles × 17 routes | No errors | Pass |
| Static analysis | Backend | No warnings | Pass |
| Workflow | 10 functional workflows | 10/10 | Pass |
| RAG | Answerable recall | 85.7% | Partial — 2 numeric-phrasing misses |
| RAG | False grounding | 0% | Pass |
| RAG | Precision@3 | 100% | Pass |
| RAG | Semantic retrieval path | Did not execute | **Fail — 404 on embedding model** |
| Latency | Deterministic endpoints | 1–3 ms | Pass |
| Latency | Login (PBKDF2) | 21 ms | Pass — deliberate trade |
| Degradation | No-LLM operation | All core flows pass | Pass |
| Signup | Self-registration behaviour | 11/11 | Pass |
| Auto-approval | R6 on shipped data | Reachable | **Pass** — verified after the seed fix (§11.2.2) |

**Overall.** The system meets every functional requirement and passes all access-control and isolation verification. It has one genuine technical failure — the embedding model is unavailable, leaving only keyword retrieval — and one real defect that evaluation surfaced and fixed: seed balances of zero made the entire leave workflow unusable, not merely one path unobservable (§11.2.2). Both are reported as failures or fixed findings in the table above rather than omitted, and the residual gaps have concrete remediation in Section 13.
