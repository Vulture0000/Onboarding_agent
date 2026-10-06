# 12. Evaluation, Comparison, and Innovation

## 12.1 What Is Being Compared

The comparison below is deliberately **not** a head-to-head benchmark against other systems. No such benchmark was run, and reporting invented comparison figures would be the single easiest way to make this report worthless. Instead, each claim is labelled with the evidence it rests on, and any claim resting on reasoning rather than measurement is marked as such.

| Label | Meaning |
|---|---|
| **[M]** | Measured in this project; a number is reported in Section 11 |
| **[D]** | Design property — verifiable by reading or by an assertion, but not a runtime measurement |
| **[R]** | Reasoning from the design; a hypothesis, not a result |

## 12.2 Comparison with Conventional Automation

The most common alternative to this system is a deterministic script or workflow tool: a résumé parser writes to a database, a cron job generates checklists, and a leave form posts to an approval queue.

| Capability | Script / workflow tool | This system | Evidence |
|---|---|---|---|
| Résumé → structured profile | Requires a separate parser; brittle on layout variation | Model extraction with regex/heuristic fallback | [D] |
| Checklist generation | Fixed template for everyone, or code branches per role | Role + department templates selected automatically | [D] |
| Scheduling against availability | Must be written and maintained per use case | Availability, hours, lunch, and conflict rules in one tool module | [D] |
| Leave rule enforcement | Reliable and fast | Identical reliability — **the same code path** | [D] |
| Policy Q&A in natural language | Not possible; requires a human to read the document | Grounded retrieval with refusal | [M] 85.7% recall, 0% false grounding |
| Multi-step composition with branching | Every branch must be anticipated in advance | Routing is a state function, evaluated at runtime | [D] |
| Adding a new agent or capability | Add a function, wire it, redeploy | Add a node + a routing predicate; supervisor unchanged | [D] |
| Failure when the LLM is unavailable | N/A | Core system unaffected; weaker extraction and retrieval only | [M] Pass |

**The honest reading of this table is that the agentic system wins on flexibility and on unstructured input, and is not faster or cheaper than a script on the deterministic paths.** Where the business problem is a fixed sequence with no judgement and no natural-language interface, a script is the better engineering choice, and this report does not claim otherwise. The agentic design earns its cost in the places where the rules are not enumerable in advance — chiefly free-text leave requests and policy questions.

**Where it would lose to a script:** a strict, high-volume, purely computational workflow with no ambiguity. There, the extra indirection of a graph and state machine is pure overhead.

## 12.3 Why the Model Is Excluded from Decisions

This is the report's central design claim, so it is argued explicitly and quantified where possible.

**The argument.** A language model is a stochastic function whose output depends on sampling and prompt context. A leave ledger is a record of entitlements. If the same request submitted twice could produce two different outcomes, the system is not usable for anything that must be defended — and a rejected leave request is exactly that.

**The implementation of the claim.** In the leave pipeline, the model contributes **at most one artefact**: the structured interpretation of a free-text request. Everything after that is arithmetic in `leave_tools`:

```
balance check        code     — compare remaining vs. required
working-day count    code     — exclude weekends, apply policy calendar
approval threshold   code     — days > 2 → human required
date validation      code     — reject ranges > 1 year in the past
status transition    code     — PENDING → APPROVED | REJECTED
idempotency guard    code     — PENDING-only, else 409
```

**The measured consequence.** Deterministic endpoints respond in **1–3 ms [M]**, with zero model calls in the request path. A workflow where the balance check were a model call would inherit the model's latency, its cost per request, its rate limits, and its variance, for the privilege of occasionally getting the arithmetic wrong.

**The two demonstrated costs of doing it the other way.** These are the project's own defects, and they are more persuasive than a hypothetical:

1. **Audit-trail corruption at a process boundary.** The human-in-the-loop flow initially recorded `decided_by = "HR Admin"` for *every* approval, because the approver's identity was dropped between the interrupt payload and the decision node. The system looked compliant and was systematically false. A prompt-based decision step would have had the same class of failure with no test to catch it.
2. **Non-determinism in a data path.** Not observed in this system, because it was designed out — which is the point. The claim is a design constraint that prevented the failure, and Section 13 keeps it as a permanent rule.

**The general rule adopted: if a wrong answer is unrecoverable or legally attributable, the model does not produce it.** That covers balances, dates, statuses, approvals, and authorisation. It does not cover extraction and phrasing.

## 12.4 Security Comparison

| Threat | Baseline process | This system | Evidence |
|---|---|---|---|
| Cross-tenant record access | Every authenticated user sees everything (P5) | Server-side scoping on every request and query; **38/38** matrix, **10/10** leakage checks | [M] |
| Privilege escalation at creation | Not addressed | Role derived from email prefix, or rejected unless an explicit `login_role` is given; **27/27** | [M] |
| Forged self-service access | N/A | `/api/me/*` derives identity from the JWT and **ignores** `employee_id` in the body | [M] |
| Unauthorized approval | Depends on discipline | Manager scope enforced on the decision path; out-of-scope → 403 | [M] |
| Double-spend of a leave balance | Possible via double submission | Status-transition guard → 409; balance deducted once | [M] |
| Password compromise | Varies | PBKDF2-HMAC-SHA256, 260,000 iterations, per-user salt | [D] |
| Role forgery via a request body | Common failure | Role is never read from the client on any endpoint | [D] |
| **Public self-registration as HR** | N/A | **Blocked at the schema** — `SignupRequest` has no role field, so `role:"HR"` in the body is ignored; verified to return `EMPLOYEE` | [M] |

**The last row is the sharpest security trade-off in the system, because it is the one place where an open door was required and a specific risk had to be closed instead.**

Self-registration is genuinely open: `POST /api/auth/signup` is unauthenticated, and a new account is created, auto-logged-in, and usable immediately. The risk is that the HR-side employee-creation flow derives roles from an **email prefix**, so naively reusing it at signup would mean anyone could type `hradmin@xyzcorp.com` and be provisioned as an HR administrator with organisation-wide visibility over every employee's record. That is a total compromise of the access model, and it would be a one-line mistake to make.

The fix is structural rather than procedural:

1. **`SignupRequest` has no `role` field at all.** The role is hardcoded to `Role.EMPLOYEE` in the handler. This is stronger than validating or stripping a submitted role, because there is no code path in which a client-supplied value could reach the role column.
2. **Escalation is a separate, authenticated action.** Manager and HR access are granted afterwards by a user who already holds it, through the existing HR-only endpoint.
3. **Verified, not assumed.** A signup request carrying `{"role":"HR","login_role":"HR"}` was issued and the resulting account was confirmed to be `EMPLOYEE`.

**A second, subtler property worth stating: signup is an account-*claiming* flow, not just a form.** If HR has already created an employee record with a given email but no login, signing up with that email attaches the login to the existing record rather than creating a second person. Without this, an employee added by HR and then registering themselves would exist twice in the database with two competing records, and the duplicate would be invisible because the two halves are stored separately. This was verified: a pre-created employee signed up, and the database still held exactly one employee row, with no regenerated task plan and no duplicated balances.

Removing `POST /api/auth/demo-accounts` — currently unauthenticated, and it discloses seeded names, emails, and roles — is listed in Section 13 as a required change before any deployment outside a local demo.

## 12.5 Innovative Aspects

Five aspects of the design are, in the author's judgement, the parts worth carrying to another project.

**1. Reliability by exclusion, not by instruction.** "Ask the model to be careful" is unenforceable. Removing the model from a decision path is enforceable and testable. This is the single most transferable idea here: *the more consequential the decision, the less the model should touch it.* It converts an untestable quality attribute into an architectural invariant.

**2. The human as a graph participant.** Approvers are modelled as a node in the workflow rather than as an out-of-band notification. The approval payload, the suspension, and the resumed execution all use the same machinery as an automated step, so an approval is auditable in the same log as an automated action, and the state at decision time is the state at request time. A status flag could imitate the behaviour; it would not preserve the context.

**3. Graceful degradation as a designed path, not an error handler.** The system has three independently degraded modes — heuristics for extraction, keyword for retrieval, no model for anything deterministic — and each is exercised by an explicit test. The consequence is that the system's availability is independent of a third-party API, which is a real operational property in any organisation that cannot tolerate a vendor outage blocking leave approval.

**4. Token-scoped role derivation with an explicit override and a hard default.** Roles are derived from a deterministic, case-insensitive, separator-tolerant rule, are previewed in the UI before submission, can be overridden by an authorised user, and — critically — **default to rejection** when the address is unrecognised. Most provisioning schemes fail on the default: an unmatched address silently becoming a low-privilege account, or worse, an elevated one. Failing closed is the correct default, and it was implemented as such.

**5. Body-inspection isolation testing.** Verifying authorisation only by status code misses the case where a `200` is returned with the wrong user's data in it — the most consequential access-control bug that does not raise an error. Inspecting response bodies for out-of-scope identifiers catches a class of defect that the conventional approach structurally cannot see, and it is what caught the `employee_id`-in-the-body design.

## 12.6 Limitations and Threats to Validity

Stated as a list, because a reader deciding whether to rely on this work needs the weak points first.

| # | Limitation | Consequence | Severity |
|---|---|---|---|
| L1 | Embedding model returns 404; FAISS path unexecuted | All RAG figures describe **keyword** retrieval. Recall is 85.7% instead of potentially higher, and semantic paraphrase is the known failure mode. | **High** |
| L2 | Corpus is 5 documents / 6.6 KB | Retrieval metrics do not transfer to a real handbook. Two of five policies are not even indexed. | **High** |
| L3 | 7-employee dataset | Latency figures reflect SQLite and small result sets; no load or concurrency testing was performed. | High |
| L4 | No user study | Adoption, time-saved, and manager-satisfaction claims are **unmeasured**. The business case in Section 2 is a mechanism argument, not an ROI calculation. | High |
| L5 | Résumé extraction tested on synthetic documents | No claim is made about accuracy on real-world PDF layouts. | Medium |
| L6 | Leave entitlement is fixed at hire with no HR adjustment path | Carry-forward (up to 30 earned days) and year-end lapse are documented but unenforced. Fixed for the seed defect; the management path is still missing. | Medium |
| L7 | `route_after_resume` matches on error **text** | Graph control flow is coupled to an error string; a rewording upstream would silently alter behaviour. | Medium |
| L8 | Demo accounts endpoint is unauthenticated | Discloses seeded identities and roles. Blocking for any non-demo deployment. | Medium |
| L9 | No notification mechanism | Approvers learn of pending requests only by visiting the UI. This is the most significant **product** gap. | Medium |
| L10 | Single-process SQLite, no migrations | Fine for a prototype; limits horizontal scaling and schema evolution. | Low |
| L11 | No load, stress, or adversarial testing | Availability and resistance to enumeration are unknown. | Low |
| L12 | Evaluation was single-run | No confidence intervals; the 12/14 result is a point estimate on a 14-query set. | Low |

**Two threats to validity deserve emphasis.** L2 and L4 together mean the strongest-looking results in this report are the least generalisable: the access-control results (38/38, 10/10) are near-binary assertions that transfer cleanly to any deployment, whereas the retrieval results depend on a corpus size chosen to make the demonstration tractable. **The 85.7% figure should not be quoted as a performance claim for the RAG component in a larger deployment.** And the evaluation is single-run on a 14-query set, where a single query is worth 7.1 percentage points — which is precisely why the mislabelled query in §11.3.4 could swing the result by 15 points with no code change.
