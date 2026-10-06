# Employee Onboarding Agent — Final Project Report

**System:** Multi-agent employee onboarding platform (Supervisor + 5 specialised agents, LangGraph, FastAPI, React)
**Repository:** https://github.com/Vulture0000/Onboarding_agent
**Commit:** `a17735f` on `main` · **Python 3.12.14 · FastAPI 0.141.1 · React 18 · LangGraph ≥0.2.60**

---

## Section index

| # | Section | File | Words | Covers |
|---|---|---|---|---|
| 1 | Introduction | `01-introduction.md` | 931 | Background, motivation, need for agentic AI, six objectives |
| 2 | Problem Statement & Business Case | `02-problem-statement.md` | 936 | Five problem statements (P1–P5), real-world context, automation business case |
| 3 | User & Stakeholder Analysis | `03-users-and-stakeholders.md` | 1,230 | Three personas, five stakeholder groups, 12 requirements with verification method |
| 4 | Proposed Agentic AI Solution | `04-solution.md` | 967 | Three architectural commitments, nine features, agent-by-agent boundary, scope exclusions |
| 5 | Dataset & Knowledge Sources | `05-dataset.md` | 896 | 5-document policy corpus (6,636 B), seeded operational data, 20-query eval set |
| 6 | Tools & Technologies Used | `06-technologies.md` | 617 | Selection rationale with rejected alternatives, full stack, ~7,400 LOC |
| 7 | Agent Architecture | `07-architecture.md` | 1,207 | 8 graph nodes, 5 tool modules, three memory mechanisms, reasoning flow |
| 8 | Agent Workflow & Orchestration | `08-workflow.md` | 1,222 | Four workflows, decomposition, coordination, interrupt/checkpoint implementation |
| 9 | RAG for Policy Answers | `09-rag.md` | 1,095 | Ingestion, hybrid retrieval with fallback, grounding, refusal contract |
| 10 | Human-in-the-Loop Leave Approval | `10-human-in-the-loop.md` | 1,176 | Design rationale, interrupt/resume, decision capture, audit trail |
| 11 | Implementation & Evaluation | `11-implementation-and-evaluation.md` | 2,775 | 10 workflows verified, 38/38 RBAC, 10/10 isolation, 27/27 provisioning, RAG + performance |
| 12 | Evaluation, Comparison & Innovation | `12-comparison-and-innovation.md` | 1,976 | Script comparison, why the model is excluded, security comparison, 5 innovations, 12 limitations |
| 13 | Future Enhancements & Conclusion | `13-future-and-conclusion.md` | 1,417 | 16-item prioritised roadmap, long-term vision, conclusion |
| | **Total** | | **16,445** | |

## Headline results

| Area | Metric | Result |
|---|---|---|
| Access control | RBAC matrix | **38 / 38** |
| Data isolation | Cross-scope leakage checks | **10 / 10** |
| Role provisioning | Email-prefix behaviour | **27 / 27** |
| Signup | Self-registration behaviour | **11 / 11** |
| Workflows | Functional end-to-end tests | **10 / 10** |
| RAG | Answerable recall | **85.7%** (12/14) |
| RAG | False grounding (out-of-corpus) | **0%** (0/6) |
| RAG | Precision@3 | **100%** |
| Latency | Deterministic endpoints | **1–3 ms** |
| Latency | Login (PBKDF2, 260k iters) | **21 ms** |
| Build | Frontend | **Pass** |
| Lint | Frontend `no-undef` / Backend `pyflakes` | **0 problems / Clean** |
| Runtime | Route crawl — 3 roles × 17 routes | **No errors** |
| Degradation | Operation with no LLM key | **Pass** |

## Three things a reader should know before relying on this

1. **The semantic retrieval path does not execute.** The configured embedding model `models/text-embedding-004` returns `404 NOT_FOUND`, so FAISS retrieval falls back to keyword search. Every RAG figure above describes the keyword path. See §9.2.1 and §12.6 (L1).
2. **The corpus is 6,636 bytes across 5 documents.** Retrieval metrics do not transfer to a production handbook. See §12.6 (L2).
3. **There is no user study.** The business case in §2 is a mechanism argument, not an ROI measurement. See §12.6 (L4).

A further caveat: the embedding model is unavailable, so the measured retrieval figures describe a keyword fallback rather than the semantic path. Separately, evaluation surfaced a real defect in the leave seed data — zero balances made the whole leave workflow unusable while the tests stayed green; it is now fixed and documented in §11.2.2.

## Page-length note

At ~16,400 words plus 20+ tables and ASCII diagrams, this renders to approximately **27–33 pages** single-spaced (11pt, 1″ margins) or **45–55 pages** double-spaced. It therefore **exceeds the 15–20 page target.**

To reach 15–20 pages, the recommended cut is §§9 and 10 (consolidate into the §7/§8 architecture discussion, −2,200 words), §3 personas (three paragraphs instead of full profiles, −700), and §12.6 (a compact table only, −500) — which preserves all measured results and the architecture and RAG design argument at roughly 12,500 words / **21–25 pages**, or at roughly 10,000 words / **18–20 pages** with a further trim of §2 and §5.

## Screenshots

Captured from the running application (Playwright/Chromium, 1440×900 @2x) and saved in `figures/`. All assertions behind them passed; see §11.2.3.

| File | Shows |
|---|---|
| `01-login.png` | Sign-in screen, demo accounts, and the **Create an account** link |
| `02-employee-dashboard.png` | Employee home — own progress, tasks, balances |
| `03-employee-tasks.png` | Employee task list |
| `04-employee-leave.png` | Employee leave and balances |
| `05-employee-meetings.png` | Employee meetings |
| `16-signup-form.png` | Signup form, with the EMPLOYEE-only notice |
| `17-signed-in-as-new-employee.png` | Landing on `/my` immediately after a fresh signup |
| `18-new-employee-tasks.png` | The auto-generated plan for the new account |

Still to capture for a complete submission:

| Figure | Section | Content |
|---|---|---|
| 1 | §7.1 | Agent graph (the ASCII diagram in `07-architecture.md` §7.1 rendered as a proper graph) |
| 2 | §8.2 | Interrupt / resume sequence diagram |
| 3 | §11.2.1 | Workflow verification results, annotated with the pending-approval UI state |
| 4 | §11.2.4 | RBAC matrix heatmap — 3 roles × protected endpoints |
| 5 | §11.2.6 | Employees → Add Employee, showing the live role preview from the email prefix |
| 6 | §10.3 | Manager's approval queue with balance and policy excerpt |
| 7 | §9.4 | Policy Q&A — a grounded answer with sources, and a refusal |

## Assembling into a single document

```bash
# In order, with a title page and a generated table of contents:
cat 01-introduction.md 02-problem-statement.md 03-users-and-stakeholders.md \
    04-solution.md 05-dataset.md 06-technologies.md 07-architecture.md \
    08-workflow.md 09-rag.md 10-human-in-the-loop.md \
    11-implementation-and-evaluation.md 12-comparison-and-innovation.md \
    13-future-and-conclusion.md > full-report.md

pandoc full-report.md -o report.docx --toc --number-sections   # if pandoc is available
```

**Do not** commit the rendered document to the repository without checking it with the marker, and never include `backend/.env` — it is gitignored, and it must stay that way.
