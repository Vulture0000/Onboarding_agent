# 4. Proposed Agentic AI Solution

## 4.1 Overall Solution

The system is a multi-agent orchestration built on LangGraph, with five specialised agents coordinated by a supervisor and one deliberate human decision point. It is exposed through a FastAPI backend and a React frontend, and it is built so that the language model is confined to the two tasks that benefit from it — parsing unstructured input and answering natural-language questions — while every business-critical decision is computed in deterministic Python.

Three architectural commitments shape everything else:

**C1 — Agents act only through tools.** No agent writes to the database directly. Every side effect goes through a function in a `tools/` layer. This makes the set of possible state changes enumerable by reading that directory, which is what makes R12 (attributable audit log) cheap to satisfy — there is exactly one place to log.

**C2 — Agents communicate only through shared graph state.** They are not independent chatbots and they do not call each other. All data passes through a single typed state object. The consequence worth noting is that an agent cannot obtain data by asking a colleague; it can only act on what the state contains, which constrains the failure modes considerably.

**C3 — The model is excluded from reproducible decisions.** Balances, date arithmetic, approval thresholds, and status transitions are computed in `app/tools/leave_tools.py` and never delegated to a prompt. A model is a stochastic function; a leave ledger is not. If the same request were sent twice, the two runs must agree.

## 4.2 Key Features

| Feature | Description |
|---|---|
| **Résumé → onboarding** | Upload a PDF; the Resume Agent extracts a structured profile, the Onboarding Agent generates a role-specific task plan, and the Calendar Agent books introductory meetings against real availability constraints. |
| **Leave with human-in-the-loop** | Requests are parsed, validated against balance and policy, and — where the policy requires it — the workflow *stops* at a LangGraph `interrupt()` and waits. A named manager or HR resumes the thread; the decision is recorded with their identity. |
| **Deterministic auto-approval** | Requests within the policy limit are approved without a human, and the balance is consumed immediately. |
| **Grounded policy Q&A** | Employee questions are answered from a FAISS index over the organisation's policy documents, with source filenames returned. Queries outside the corpus are refused rather than answered from model priors. |
| **Role-based access control** | Three roles (Employee, Manager, HR) with server-side enforcement on every request *and* on every query. |
| **Self-service scope** | A dedicated `/me/*` surface derives the employee from the JWT, ignoring any `employee_id` in the request body. |
| **Email-prefix role assignment** | Adding a user provisions their login and derives the access role from the text before the employee id in their email address. |
| **Self-service signup (EMPLOYEE only)** | Anyone can register and is signed in immediately, receiving a generated onboarding plan, task list and leave balances. The role is hardcoded server-side and cannot be self-selected. If HR already created the person, signup links the login to that existing record instead of duplicating it. |
| **Graceful degradation** | With no API key, extraction falls back to heuristics, retrieval falls back to keyword search, and all CRUD/leave/calendar logic is unaffected. |
| **Agent activity audit** | Every automated step is persisted with agent, action, affected employee, and outcome. |

## 4.3 Agent-Based Approach

The five agents are separated by *responsibility*, and each is deliberately small. The design principle is that an agent should be the smallest component that fully owns one domain concern, because every additional agent adds a routing decision that can be wrong.

| Agent | Responsibility | Model usage | Why this boundary |
|---|---|---|---|
| **Supervisor** | Classifies the request, routes via conditional edges | Intent classification only, with a keyword fallback | Routing errors are the most damaging class of error, so routing has a deterministic fallback |
| **Resume Agent** | PDF → text → structured profile → employee record | Extraction only, regex/heuristic fallback | Parsing unstructured documents is the LLM's strongest suit; but it never makes hiring judgements |
| **Onboarding Agent** | Generates role/department-aware task plan | **None** | Templates are deterministic; a model would add variance to a checklist |
| **Calendar Agent** | Schedules against availability, work hours, lunch, conflicts | **None** | Slot finding is arithmetic; models are worse at it and non-reproducible |
| **Leave Agent** | Parses request, consults policy, applies rules, interrupts for approval | Natural-language parsing only | Parsing "next Friday for two days off, family thing" is hard; deciding whether that is valid is arithmetic |
| **Policy / RAG Agent** | FAISS retrieval, grounded answer | Answering from retrieved chunks | Grounding is the mitigation for hallucination; the model never supplies policy facts from memory |

**The single most important entry in this table is the three cells that read "None".** The Onboarding, Calendar, and Leave agents do their actual work without a model. This is not an oversight or an unfinished feature — it is the design. The Leave Agent *does* use a model, but only to turn a sentence into structured dates; the balance check, the approval threshold, and the status transition are all code. An experiment in Section 12 quantifies what excluding the model buys.

## 4.4 Scope Boundaries

Stating what the system deliberately does not do is part of the design:

- **No hiring decisions.** The Resume Agent extracts what a document says. It does not evaluate or rank candidates. Recruitment was out of scope and is an area where automated judgement carries the highest risk.
- **No payroll, performance review, or disciplinary workflow.** These have different regulatory and fairness constraints.
- **No email or chat integration.** Approvals happen in the UI. Notifications are identified as future work in Section 13.
- **Self-service registration is EMPLOYEE-only.** Signup is open to anyone, but the role is hardcoded to `EMPLOYEE` server-side and is never read from the request. Manager and HR access is granted afterwards by an existing privileged user. See Section 12.4.
